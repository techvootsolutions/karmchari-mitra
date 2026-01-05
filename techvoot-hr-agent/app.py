from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from omnidimension import Client
from config import Config
import database
from auth import auth_bp, login_manager

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Initialize database
database.init_database()

# Initialize Login Manager
login_manager.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')

# Routes
@app.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    status_filter = request.args.get('status', 'all')
    
    stats = database.get_dashboard_stats()
    chart_data = database.get_chart_data()
    pending_candidates = database.get_pending_candidates()
    evaluated_calls = database.get_recent_calls_with_scores(status_filter=status_filter)
    
    return render_template('dashboard.html',
                         candidates=pending_candidates,
                         evaluated_calls=evaluated_calls,
                         stats=stats,
                         chart_data=chart_data,
                         company_name=Config.COMPANY_NAME,
                         current_filter=status_filter)

@app.route('/candidates')
@login_required
def candidates():
    """All candidates page"""
    all_candidates = database.get_all_candidates()
    return render_template('candidates.html', candidates=all_candidates)

@app.route('/add_candidate', methods=['GET', 'POST'])
@login_required
def add_candidate():
    """Add new candidate"""
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        job_title = request.form.get('job_title')
        
        if name and phone and job_title:
            candidate_id = database.add_new_candidate(name, phone, email, job_title)
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    
    return render_template('add_candidate.html')

@app.route('/candidate/<int:candidate_id>')
@login_required
def candidate_detail(candidate_id):
    """Candidate detail page"""
    candidate = database.get_candidate_by_id(candidate_id)
    if not candidate:
        flash("Candidate not found or has been deleted.", "warning")
        return redirect(url_for('dashboard'))
        
    call_logs = database.get_call_logs(candidate_id)
    
    return render_template('candidate_detail.html', candidate=candidate, call_logs=call_logs)

@app.route('/reports')
@login_required
def reports():
    """Reports page"""
    daily_stats = database.get_daily_stats_report()
    status_dist = database.get_status_distribution()
    
    return render_template('reports.html', 
                         daily_stats=daily_stats,
                         status_dist=status_dist)

@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/settings/rules')
@login_required
def settings_rules():
    """View and manage hiring rules"""
    conn = database.get_db_connection()
    rules = conn.execute('SELECT * FROM job_rules').fetchall()
    conn.close()
    return render_template('rules.html', rules=rules)

@app.route('/settings/rules/add', methods=['POST'])
@login_required
def add_rule():
    role = request.form.get('role_keyword')
    min_yrs = request.form.get('min_years', 0)
    max_yrs = request.form.get('max_years', 100)
    max_sal = request.form.get('max_salary', 0)
    questions = request.form.get('custom_questions', '')
    
    conn = database.get_db_connection()
    conn.execute('INSERT INTO job_rules (role_keyword, min_years, max_years, min_salary, max_salary, custom_questions) VALUES (?, ?, ?, ?, ?, ?)',
                (role, min_yrs, max_yrs, 0, max_sal, questions))
    conn.commit()
    conn.close()
    flash('Rule added successfully!', 'success')
    return redirect('/settings/rules')

@app.route('/settings/rules/delete/<int:rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    conn = database.get_db_connection()
    conn.execute('DELETE FROM job_rules WHERE id = ?', (rule_id,))
    conn.commit()
    conn.close()
    flash('Rule deleted.', 'success')
    return redirect('/settings/rules')

# API Routes
@app.route('/api/add_candidate', methods=['POST'])
@login_required
def api_add_candidate():
    """API endpoint to add candidate"""
    data = request.json
    
    if not data or 'name' not in data or 'phone' not in data or 'job_title' not in data:
        return jsonify({"success": False, "error": "Missing required fields"})
    
    candidate_id = database.add_new_candidate(
        data['name'],
        data['phone'],
        data.get('email', ''),
        data['job_title']
    )
    
    return jsonify({"success": True, "id": candidate_id})

@app.route('/api/export_sheets', methods=['POST'])
@login_required
def api_export_sheets():
    """Export data to Google Sheets"""
    try:
        import sheets_integration
        count = sheets_integration.export_to_sheets()
        return jsonify({"success": True, "message": f"Exported {count} new rows."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/import_sheets', methods=['POST'])
@login_required
def api_import_sheets():
    """Import data FROM Google Sheets"""
    try:
        import sheets_integration
        # 1. Sync Provider -> Sheet
        sheets_integration.export_to_sheets()
        # 2. Sync Sheet -> DB
        count = sheets_integration.import_from_sheets()
        return jsonify({"success": True, "message": f"Synced & Imported {count} rows."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/parse_resume', methods=['POST'])
@login_required
def api_parse_resume():
    """Parse uploaded resume"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"})
        
    try:
        from utils.resume_parser import parse_resume
        # Read file into memory
        import io
        file_stream = io.BytesIO(file.read())
        data = parse_resume(file_stream, file.filename)
        
        if "error" in data:
            return jsonify({"success": False, "error": data["error"]})
            
        return jsonify({"success": True, "data": data})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/delete_candidate/<int:candidate_id>', methods=['DELETE'])
@login_required
def api_delete_candidate(candidate_id):
    """Delete a candidate and their logs"""
    try:
        database.delete_candidate(candidate_id)
        return jsonify({"success": True, "message": "Candidate deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/import_resume', methods=['POST'])
@login_required
def api_import_resume():
    """Parse and immediately save resume (Bulk Import)"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"})
        
    try:
        from utils.resume_parser import parse_resume
        # Read file into memory
        import io
        file_stream = io.BytesIO(file.read())
        data = parse_resume(file_stream, file.filename)
        
        if "error" in data:
            return jsonify({"success": False, "error": data["error"]})
            
        # Auto-save to DB
        name = data.get('name') or "Unknown Candidate"
        phone = data.get('phone') or ""
        email = data.get('email') or ""
        job_title = data.get('job_title') or "Candidate"
        
        # Avoid duplicates (basic check by phone)
        # In a real app we'd query DB, but for now just rely on user or DB constraints if any
        # Let's check DB to be safe
        conn = database.get_db_connection()
        existing = conn.execute('SELECT id FROM candidates WHERE phone = ?', (phone,)).fetchone()
        
        if existing and phone:
             conn.close()
             return jsonify({"success": False, "error": f"Duplicate phone: {phone}"})
        
        conn.close()
        
        candidate_id = database.add_new_candidate(name, phone, email, job_title)
        
        return jsonify({
            "success": True, 
            "message": "Imported successfully",
            "candidate": {
                "id": candidate_id,
                "name": name,
                "job_title": job_title
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/start_queue', methods=['POST'])
@login_required
def api_start_queue():
    """Start bulk calling queue"""
    try:
        pending_candidates = database.get_pending_candidates()
        
        if not pending_candidates:
            return jsonify({"success": False, "message": "No pending candidates found"})
            
        results = {
            "total": len(pending_candidates),
            "initiated": 0,
            "failed": 0,
            "errors": []
        }
        
        client = Client(Config.OMNIDIMENSION_API_KEY)
        
        for candidate in pending_candidates:
            try:
                # Dispatch call
                response = client.call.dispatch_call(
                    agent_id=int(Config.OMNIDIMENSION_AGENT_ID),
                    to_number=candidate['phone']
                )
                
                # Extract external ID (Try dict access or attribute)
                external_id = None
                if isinstance(response, dict):
                    external_id = response.get('call_log_id') or response.get('id')
                else:
                    external_id = getattr(response, 'call_log_id', None) or getattr(response, 'id', None)
                
                if not external_id:
                     print(f"Warning: Could not extract ID from response: {response}")
                
                # Log attempt
                database.log_call(
                    candidate['id'], 
                    "initiated", 
                    0, 
                    "Bulk call initiated", 
                    external_call_id=external_id
                )
                results["initiated"] += 1
                
            except Exception as e:
                print(f"Failed to call {candidate['name']}: {e}")
                results["failed"] += 1
                results["errors"].append(f"{candidate['name']}: {str(e)}")
                
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/sync_calls', methods=['POST'])
@login_required
def api_sync_calls():
    """Sync status of initiated calls from Omnidimension"""
    try:
        initiated_logs = database.get_initiated_calls()
        if not initiated_logs:
            return jsonify({"success": True, "message": "No calls to sync", "updated": 0})
            
        client = Client(Config.OMNIDIMENSION_API_KEY)
        updated_count = 0
        
        for log in initiated_logs:
            external_id = log['external_call_id']
            if not external_id:
                continue
                
            try:
                # Fetch detailed log
                call_details = client.call.get_call_log(call_log_id=external_id)
                
                # Normalize response (handle dict vs object)
                if not isinstance(call_details, dict) and hasattr(call_details, '__dict__'):
                   call_details = call_details.__dict__
                
                # Check status
                status = call_details.get('status')
                # Map Omnidimension status to our status
                # finalized, completed, answered -> contacted
                # no-answer, failed -> not_interested (or keep pending?)
                
                final_outcome = None
                if status in ['completed', 'finalized']:
                    final_outcome = 'contacted'
                elif status in ['failed', 'no-answer', 'busy']:
                    final_outcome = 'not_interested'
                
                    if final_outcome:
                        duration = call_details.get('duration_seconds', 0)
                        transcript = call_details.get('transcript', '') or ""
                        recording = call_details.get('recording_url', '')
                        
                        print(f"DEBUG: Processing Call {external_id}")
                        print(f"DEBUG: Duration: {duration} (Type: {type(duration)})")
                        print(f"DEBUG: Transcript: {transcript[:50]}...")

                        # Ensure duration is int
                        try:
                            duration = int(float(duration))
                        except:
                            duration = 0

                        # AI Scoring Logic
                        score = 0
                        analysis_points = []
                        
                        # 1. Duration Score (Max 50)
                        # 5 mins (300s) = 50 pts
                        dur_score = min(int((duration / 300) * 50), 50)
                        score += dur_score
                        print(f"DEBUG: Duration Score: {dur_score}")

                        if dur_score > 30:
                            analysis_points.append("Good call duration")
                        
                        # 2. Keyword/Sentiment Analysis (Max 50)
                        keywords = ['interested', 'available', 'join', 'salary', 'experience', 'relocate', 'thank you', 'yes', 'great', 'interview']
                        found_keywords = [w for w in keywords if w in transcript.lower()]
                        keyword_count = len(found_keywords)
                        key_score = min(keyword_count * 10, 50)
                        score += key_score
                        print(f"DEBUG: Keyword Score: {key_score} (Keywords: {found_keywords})")
                        
                        if found_keywords:
                            analysis_points.append(f"Keywords: {', '.join(found_keywords[:3])}")
                            
                        analysis = ". ".join(analysis_points)
                        if not analysis:
                            analysis = "No significant data"
                    
                    database.update_call_log(
                        external_id, 
                        final_outcome, 
                        duration, 
                        transcript, 
                        recording,
                        score,
                        analysis
                    )
                    
                    updated_count += 1
                    
            except Exception as e:
                print(f"Error syncing call {external_id}: {e}")
        
        return jsonify({"success": True, "updated": updated_count})
        
    except Exception as e:
        print(f"Sync failed: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/make_call', methods=['POST'])
@login_required
def api_make_call():
    """Initiate a call to a single candidate with dynamic context"""
    data = request.json
    candidate_id = data.get('candidate_id')
    
    conn = database.get_db_connection()
    c = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
    
    # helper to find rule
    role = str(c['job_title']).lower()
    rules = conn.execute('SELECT * FROM job_rules').fetchall()
    conn.close()
    
    questions = ""
    # Find matching rule
    for r in rules:
        if r['role_keyword'].lower() in role:
            questions = r['custom_questions'] or ""
            break
            
    if not c:
        return jsonify({"success": False, "error": "Candidate not found"})
        
    try:
        client = Client(Config.OMNIDIMENSION_API_KEY)
        
        # Prepare Context
        # We pass 'custom_questions' variable to the agent
        # The Agent Prompt should be configured to use {{custom_questions}}
        call_context = {
            "candidate_name": c['name'],
            "job_position": c['job_title'],
            "custom_questions": questions
        }
        
        print(f"Dispatching call to {c['name']} ({c['job_title']}) with questions: {questions[:30]}...")

        response = client.call.dispatch_call(
            agent_id=int(Config.OMNIDIMENSION_AGENT_ID),
            to_number=c['phone'],
            call_context=call_context
        )
        
        # ... rest of the function (update database, log call) ...
        # (Need to make sure we don't duplicate logic, copying relevant parts)
        
        # Extract ID (Omnidimension returns object or dict)
        if hasattr(response, 'id'):
            call_id = response.id
        elif isinstance(response, dict):
            call_id = response.get('id')
        else:
            # Fallback if structure is different
            print(f"Unexpected response type: {type(response)}")
            call_id = "unknown_id"
            
        # Update candidate status
        database.update_candidate_status(candidate_id, 'contacted')
        
        # Log the call
        database.log_call(candidate_id, "initiated", external_call_id=call_id)
        
        return jsonify({"success": True, "message": "Call initiated", "call_id": call_id})
        
    except Exception as e:
        print(f"Call Error: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/call-script/<int:candidate_id>')
@login_required
def call_script(candidate_id):
    """Generate call script for candidate"""
    candidate = database.get_candidate_by_id(candidate_id)
    
    if not candidate:
        return "Candidate not found"
    
    script = f"""
    Candidate: {candidate['name']}
    Phone: {candidate['phone']}
    Position: {candidate['job_title']}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    INTRODUCTION:
    "Hello {candidate['name']}, this is Techvootbot from Techvoot Solution.
    I hope I'm catching you at a good time?"
    
    PURPOSE:
    "I'm calling to follow up on your resume submission for the {candidate['job_title']} position."
    
    QUESTIONS:
    1. "Could you please give us a brief introduction about yourself?"
    2. "May I know your current position and responsibilities?"
    3. "What is your current salary package?"
    4. "What would be your expected salary for this role?"
    5. "What is your notice period with your current employer?"
    
    CLOSING:
    "Thank you for sharing this information. We'll review your details and get back to you soon."
    """
    
    transcript = database.get_last_transcript(candidate_id)
    
    return render_template('call_script.html', 
                         script=script, 
                         candidate=candidate,
                         transcript=transcript,
                         company_name=Config.COMPANY_NAME)

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=5000, debug=True)