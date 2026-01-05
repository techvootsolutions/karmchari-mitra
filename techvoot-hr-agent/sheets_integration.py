import gspread
from oauth2client.service_account import ServiceAccountCredentials
from omnidimension import Client
from config import Config
import database
import json

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    # Open the sheet - ensure the user created it with this name
    return client.open("Techvoot HR Data").sheet1

import re

def get_hiring_rules():
    """Fetch criteria from database"""
    conn = database.get_db_connection()
    rules = conn.execute('SELECT * FROM job_rules').fetchall()
    conn.close()
    return rules

def evaluate_candidate(payload, rules):
    """
    Evaluate if candidate is selected based on dynamic rules.
    """
    # Extract variables
    variables = payload.get('variables', {})
    expected_salary_str = str(variables.get('expected_salary', '0'))
    current_position = str(variables.get('current_position', '')).lower()
    job_position = str(variables.get('job_position', '')).lower()
    # brief_intro = str(variables.get('brief_introduction', '')).lower() # Could check years here via regex

    # Parse Salary
    clean_salary = 0
    try:
        norm_sal = expected_salary_str.lower().replace(',', '').replace('$', '').replace('rs', '').strip()
        if 'k' in norm_sal:
            clean_salary = float(norm_sal.replace('k', '')) * 1000
        elif 'lpa' in norm_sal:
             # simplistic assumption: 12 LPA -> 12 * 100000 / 12 ~ 100k/month? Or assume annual?
             # Let's stick to simple numbers/k for now as per user examples. 
             clean_salary = float(re.findall(r'[\d\.]+', norm_sal)[0]) * 100000 
        else:
             matches = re.findall(r'[\d\.]+', norm_sal)
             if matches:
                 clean_salary = float(matches[0])
    except:
        pass
    
    # Check against ALL rules. If ANY match the role, apply its constraints.
    # If no rule matches the role, generic acceptance or Manual Review?
    # Let's say: If matched role, apply constraints. If failed -> No.
    # If not matched any role -> "Manual Review" (or Yes default).
    
    matched_rule = None
    
    for rule in rules:
        keyword = rule['role_keyword'].lower()
        if keyword in current_position or keyword in job_position:
            matched_rule = rule
            break
            
    if matched_rule:
        # Check Salary Budget
        max_budget = matched_rule['max_salary']
        if max_budget > 0 and clean_salary > max_budget:
             return f"No (Over Budget {max_budget})"
             
        # Check Experience (This is hard without parsed years, skipping for now or adding basic regex later)
        # min_years = matched_rule['min_years']
        # if parsed_years < min_years: return "No (Exp)"
        
        return "Yes"
        
    return "Manual Review"

def export_to_sheets():
    try:
        sheet = get_sheet()
        
        # Define headers based on actual sheet columns
        headers = [
            "call_id", "call_date", "phone_number", "call_request_id", "bot_name",
            "to_number", "from_number", "recording_url", "call_direction", "call_status",
            "call_transfered_status", "summary", "sentiment", "brief_introduction",
            "current_position", "current_salary", "expected_salary", "notice_period",
            "username", "job_position", "interaction_count_total", "full_conversation",
            "user_name", "call_duration_in_seconds", "call_duration_in_minutes",
            "applicant_name", "introduction_details", "candidate_intro"
        ]
        
        # Check if headers exist, if not add them
        existing_headers = sheet.row_values(1)
        if not existing_headers:
            sheet.append_row(headers)
            
        # Get existing call IDs to avoid duplicates
        try:
            existing_ids = sheet.col_values(1)[1:] # Skip header
        except:
            existing_ids = []
            
        # Fetch Rules
        rules = get_hiring_rules()
        
        # Fetch from API (Source of Truth)
        client = Client(Config.OMNIDIMENSION_API_KEY)
        print("Fetching recent calls from Omnidimension API...")
        remote_logs = []
        try:
            # We use list_calls or get_call_logs depending on library version, 
            # assuming get_call_logs based on previous inspection
            remote_logs = client.call.get_call_logs(page_size=50, agent_id=Config.OMNIDIMENSION_AGENT_ID)
            print(f"API Returned Type: {type(remote_logs)}")
            if isinstance(remote_logs, dict):
                 # print(f"Keys: {remote_logs.keys()}")
                 if 'json' in remote_logs:
                     remote_logs = remote_logs['json']
                     
                 # Now check for data/results list inside the json payload
                 if isinstance(remote_logs, dict):
                     if 'results' in remote_logs:
                         remote_logs = remote_logs['results']
                     elif 'calls' in remote_logs:
                         remote_logs = remote_logs['calls']
                     elif 'data' in remote_logs:
                         remote_logs = remote_logs['data']
                     elif 'call_log_data' in remote_logs:
                         remote_logs = remote_logs['call_log_data']
                     
            if remote_logs and isinstance(remote_logs, list):
                print(f"First Item Type: {type(remote_logs[0])}")
                if len(remote_logs) > 0:
                    print(f"First Log Keys: {remote_logs[0].keys()}")
                print(f"Total Remote Logs Fetched: {len(remote_logs)}")
                print(f"Existing IDs in Sheet: {existing_ids}")
        except Exception as e:
            print(f"API Fetch Error: {e}")
            return 0

        rows_to_add = []
            
        for log in remote_logs:
            # Normalize log object to dict if needed
            if not isinstance(log, dict):
                 if hasattr(log, '__dict__'):
                     log = log.__dict__
                 # If still not dict, try getattr for specific fields
                 
            # Extract External ID safely
            val_id = log.get('id') or log.get('call_log_id') or getattr(log, 'id', '') or getattr(log, 'call_log_id', '')
            external_id = str(val_id)
            
            if not external_id:
                continue
                
            # Strict check: ensure we don't duplicate
            if external_id in existing_ids:
                continue
                
            print(f"Exporting new call {external_id}...")
                
            print(f"Fetching details for {external_id}...")
            
            try:
                # Fetch full details from API
                details = client.call.get_call_log(call_log_id=external_id)
                if not isinstance(details, dict) and hasattr(details, '__dict__'):
                    details = details.__dict__
               
                # Extract variables (this is where the specific answers live)
                variables = details.get('variables', {})
                
                # Evaluate Selection
                selected_status = evaluate_candidate(details, rules)
                
                # Calculate durations
                duration_sec = details.get('call_duration', 0)
                try: duration_sec = int(duration_sec)
                except: duration_sec = 0
                duration_min = round(duration_sec / 60, 2)

                # Extract specific fields
                row = [
                    external_id,
                    details.get('created_at', log.get('time_of_call', '')),
                    details.get('to_number', ''), # mobile
                    details.get('campaign_id', ''), # call_request_id placeholder
                    Config.AGENT_NAME, # bot_name
                    details.get('to_number', ''),
                    details.get('from_number', ''),
                    details.get('recording_url', ''),
                    details.get('direction', 'outbound'),
                    details.get('status', ''),
                    "No", # call_transfered_status default
                    details.get('summary', ''),
                    details.get('sentiment', ''),
                    
                    # Extracted answers from variables
                    variables.get('brief_introduction', 'Not provided'),
                    variables.get('current_position', 'Not provided'),
                    variables.get('current_salary', 'Not provided'),
                    variables.get('expected_salary', 'Not provided'),
                    variables.get('notice_period', 'Not provided'),
                    
                    details.get('user_name', 'Not provided'), # username
                    variables.get('job_position', 'Not provided'), # job_position
                    details.get('interaction_count', 0),
                    details.get('call_conversation', details.get('transcript', '')), # full_conversation keys check
                    details.get('user_name', ''), # user_name again
                    
                    # New Columns Mapping
                    duration_sec, # call_duration_in_seconds
                    duration_min, # call_duration_in_minutes
                    details.get('user_name', ''), # applicant_name
                    variables.get('introduction_details', ''), # introduction_details
                    variables.get('candidate_intro', '') # candidate_intro
                ]
                
                rows_to_add.append(row)
                
            except Exception as e:
                print(f"Error fetching {external_id}: {e}")
                
        if rows_to_add:
            sheet.append_rows(rows_to_add)
            return len(rows_to_add)
        return 0

    except Exception as e:
        raise e


def import_from_sheets():
    """
    Import data FROM sheets to DB.
    Implements Smart Scoring & Qualification.
    """
    try:
        sheet = get_sheet()
        all_records = sheet.get_all_records()
        
        # Get Rules
        rules = get_hiring_rules()
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        
        for record in all_records:
            external_id = str(record.get('call_id', ''))
            phone = str(record.get('phone_number', ''))
            
            if not external_id or not phone:
                continue
                
            # Check exist
            existing_log = conn.execute('SELECT id FROM call_logs WHERE external_call_id = ?', (external_id,)).fetchone()
            if existing_log:
                continue
                
            # Find/Create Candidate
            # Normalize phone for search (remove non-digits)
            clean_phone_sheet = re.sub(r'\D', '', phone)
            last_10 = clean_phone_sheet[-10:] if len(clean_phone_sheet) >= 10 else clean_phone_sheet
            
            candidate = None
            # Try exact match first
            row = conn.execute('SELECT id, phone FROM candidates WHERE phone = ?', (phone,)).fetchone()
            if row:
                candidate = row
            else:
                # Try finding by suffix (slow but effective for mismatches like +91 vs 0)
                # We fetch all phones and match in python to avoid complex SQL regex
                all_cands = conn.execute('SELECT id, phone FROM candidates').fetchall()
                for c in all_cands:
                    c_phone_clean = re.sub(r'\D', '', c['phone'])
                    if c_phone_clean.endswith(last_10):
                        candidate = c
                        break
            
            candidate_id = None
            if candidate:
                candidate_id = candidate['id']
            else:
                name = record.get('applicant_name') or record.get('user_name') or "Unknown"
                job = record.get('job_position') or "Candidate"
                cursor.execute('INSERT INTO candidates (name, phone, email, job_title, status) VALUES (?, ?, ?, ?, "pending")', 
                              (name, phone, "", job))
                candidate_id = cursor.lastrowid
            
            # --- INTELLIGENT SCORING ENGINE ---
            
            # 1. Extract Data
            duration = 0
            try: duration = int(record.get('call_duration_in_seconds', 0))
            except: pass
            
            transcript = record.get('full_conversation', '')
            summary = record.get('summary', '')
            sentiment = record.get('sentiment', 'Neutral')
            
            # Parse Salary (Expected)
            expected_salary = 0
            exp_salary_str = str(record.get('expected_salary', ''))
            try:
                # Remove commas, currency
                clean_sal = re.sub(r'[^\d.]', '', exp_salary_str.lower().split('lpa')[0].split('k')[0])
                if clean_sal:
                    expected_salary = float(clean_sal)
                    # Normalization heuristic: if < 100, assume LPA or K? 
                    # Let's assume input like "5,00,000" -> 500000. 
                    # If "12" (meaning 12 LPA) -> 12 * 100000 / 12 = 100000/mo? 
                    # For safety, let's treat raw numbers.
            except: pass
            
            # Parse Experience from Intro (Heuristic)
            experience_years = 0
            intro = str(record.get('introduction_details', '')) + " " + str(record.get('brief_introduction', ''))
            try:
                # Look for "X years" or "X + Y experience"
                # Matches: "5 years", "5+ experience", "5 + 4 experience"
                matches = re.findall(r'(\d+)\s*(?:\+|plus)?\s*(?:years|yrs|experience)', intro.lower())
                if matches:
                    experience_years = sum([int(m) for m in matches])
                else:
                    # Fallback: look for just digits near "experience"
                    matches = re.findall(r'experience.*?(\d+)', intro.lower())
                    if matches: experience_years = int(matches[0])
            except: pass
            
            # 2. Find Matching Rule
            job_role = str(record.get('job_position', '')).lower()
            matched_rule = None
            for r in rules:
                if r['role_keyword'].lower() in job_role or r['role_keyword'].lower() in intro.lower():
                    matched_rule = r
                    break
            
            # 3. Calculate Score
            score = 50 # Base Score
            analysis_reasons = []
            
            if matched_rule:
                # Salary Check
                max_budget = matched_rule['max_salary']
                if expected_salary > 0 and max_budget > 0:
                    if expected_salary <= max_budget:
                        score += 25
                        analysis_reasons.append("✅ Within Budget")
                    elif expected_salary <= (max_budget * 1.2):
                        score += 5
                        analysis_reasons.append("⚠️ Slightly over budget")
                    else:
                        score -= 30
                        analysis_reasons.append(f"❌ Over budget (Req: {expected_salary}, Max: {max_budget})")
                
                # Experience Check
                min_exp = matched_rule['min_years']
                if experience_years > 0:
                    if experience_years >= min_exp:
                        score += 25
                        analysis_reasons.append("✅ Experience met")
                    else:
                        score -= 20
                        analysis_reasons.append(f"❌ Low Experience ({experience_years} yrs)")
            else:
                analysis_reasons.append("ℹ️ No specific rule matched")
                
            # Sentiment Bonus
            if 'positive' in sentiment.lower():
                score += 10
            elif 'negative' in sentiment.lower():
                score -= 10
                
            # Duration Check
            if duration > 180: # > 3 mins
                score += 10
            elif duration < 60:
                score -= 10
                analysis_reasons.append("⚠️ Short call")

            # Interaction Count Score (Rate out of 10)
            interaction_count = 0
            try: interaction_count = int(record.get('interaction_count_total', 0))
            except: pass
            
            # Logic: > 20 interactions = 10/10. 10 interactions = 5/10.
            # We add this 'rating' to the total score? Or just bonus?
            # Let's add it as a bonus component to the main score.
            # Max 10 points. 
            interaction_score = min(int(interaction_count / 2), 10)
            score += interaction_score
            if interaction_count > 15:
                analysis_reasons.append(f"🔥 Engaging ({interaction_count} msgs)")

            # Final Clamp
            score = max(0, min(100, score))
            
            # 4. Determine Status
            final_status = 'contacted' # default
            if score >= 80:
                final_status = 'qualified'
            elif score >= 50:
                final_status = 'on_hold'
            elif score < 50:
                final_status = 'rejected'
             
            # Special case: not interested
            call_status = str(record.get('call_status', '')).lower()
            if call_status in ['failed', 'busy', 'no-answer']:
                final_status = 'not_interested' # Override
                score = 0
            
            analysis_text = f"Status: {final_status.title()}. " + ", ".join(analysis_reasons)
            
            # Insert Log
            cursor.execute('''
                INSERT INTO call_logs (candidate_id, call_time, outcome, duration, notes, transcript, recording_url, external_call_id, score, analysis, interaction_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (candidate_id, record.get('call_date'), final_status, duration, "Imported from Sheet", 
                  transcript, record.get('recording_url'), external_id, score, analysis_text, interaction_count))
            
            # Update Candidate
            cursor.execute('UPDATE candidates SET status = ?, last_call_date = ? WHERE id = ?', 
                          (final_status, record.get('call_date'), candidate_id))
            
            imported_count += 1
            
        conn.commit()
        conn.close()
        return imported_count
        
    except Exception as e:
        print(f"Import Error: {e}")
        return 0


if __name__ == "__main__":
    # count = export_to_sheets()
    # print(f"Exported {count} new rows.")
    count = import_from_sheets()
    print(f"Imported {count} rows from sheet.")
