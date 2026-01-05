import sqlite3
from datetime import datetime

DB_PATH = 'hr_candidates.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Candidates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            job_title TEXT NOT NULL,
            current_position TEXT,
            current_salary REAL,
            expected_salary REAL,
            notice_period TEXT,
            status TEXT DEFAULT 'pending',
            call_attempts INTEGER DEFAULT 0,
            last_call_date DATETIME,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Call logs table (Enhanced for Phase 4)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            call_time DATETIME,
            outcome TEXT,
            duration INTEGER,
            notes TEXT,
            transcript TEXT,
            recording_url TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')
    
    # Users table (For Phase 2: Auth)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def get_all_candidates():
    conn = get_db_connection()
    candidates = conn.execute('SELECT * FROM candidates ORDER BY created_at DESC').fetchall()
    conn.close()
    return candidates

def get_pending_candidates():
    conn = get_db_connection()
    candidates = conn.execute(
        'SELECT * FROM candidates WHERE status = "pending" ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return candidates

def get_candidate_by_id(candidate_id):
    conn = get_db_connection()
    candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
    conn.close()
    return candidate

def add_new_candidate(name, phone, email, job_title):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO candidates (name, phone, email, job_title, status) VALUES (?, ?, ?, ?, "pending")',
        (name, phone, email, job_title)
    )
    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return candidate_id

def delete_candidate(candidate_id):
    conn = get_db_connection()
    # Delete related logs first
    conn.execute('DELETE FROM call_logs WHERE candidate_id = ?', (candidate_id,))
    # Delete candidate
    conn.execute('DELETE FROM candidates WHERE id = ?', (candidate_id,))
    conn.commit()
    conn.close()

def log_call(candidate_id, outcome, duration=0, notes="", transcript=None, recording_url=None, external_call_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''INSERT INTO call_logs 
           (candidate_id, call_time, outcome, duration, notes, transcript, recording_url, external_call_id, interaction_count) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (candidate_id, datetime.now(), outcome, duration, notes, transcript, recording_url, external_call_id, 0)
    )
    
    # Update candidate status
    cursor.execute(
        'UPDATE candidates SET status = ?, last_call_date = ?, call_attempts = call_attempts + 1 WHERE id = ?',
        (outcome, datetime.now(), candidate_id)
    )
    
    conn.commit()
    conn.close()

def update_call_log(external_call_id, outcome, duration, transcript, recording_url=None, score=0, analysis=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update log
    cursor.execute(
        '''UPDATE call_logs 
           SET outcome = ?, duration = ?, transcript = ?, recording_url = ?, score = ?, analysis = ?
           WHERE external_call_id = ?''',
        (outcome, duration, transcript, recording_url, score, analysis, external_call_id)
    )
    
    # Use the external_id to find candidate_id and update their status too
    log = conn.execute('SELECT candidate_id FROM call_logs WHERE external_call_id = ?', (external_call_id,)).fetchone()
    if log:
        cursor.execute(
            'UPDATE candidates SET status = ? WHERE id = ?',
            (outcome, log['candidate_id'])
        )
        
    conn.commit()
    conn.close()

def update_candidate_status(candidate_id, status):
    """Update candidate status and last call date"""
    conn = get_db_connection()
    conn.execute('UPDATE candidates SET status = ?, last_call_date = ? WHERE id = ?', 
                (status, datetime.now(), candidate_id))
    conn.commit()
    conn.close()

def get_initiated_calls():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM call_logs WHERE outcome = "initiated" AND external_call_id IS NOT NULL').fetchall()
    conn.close()
    return logs


def get_call_logs(candidate_id):
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM call_logs WHERE candidate_id = ? ORDER BY call_time DESC', (candidate_id,)).fetchall()
    conn.close()
    return logs

def get_recent_calls_with_scores(limit=20, status_filter='all'):
    conn = get_db_connection()
    
    query = '''
        SELECT c.id, c.name, c.job_title, l.score, l.analysis, l.outcome, l.transcript, l.external_call_id, l.call_time, l.interaction_count
        FROM call_logs l
        JOIN candidates c ON l.candidate_id = c.id
        WHERE l.outcome != 'pending' 
    '''
    
    params = []
    
    if status_filter != 'all':
        query += " AND l.outcome = ?"
        params.append(status_filter)
        
    query += " ORDER BY l.call_time DESC LIMIT ?"
    params.append(limit)
    
    calls = conn.execute(query, params).fetchall()
    conn.close()
    return calls

def get_dashboard_stats():
    conn = get_db_connection()
    all_candidates = conn.execute('SELECT * FROM candidates').fetchall()
    
    calls_today = conn.execute("SELECT COUNT(*) FROM call_logs WHERE DATE(call_time) = DATE('now')").fetchone()[0]
    
    # Convert Row objects to dicts for list comprehension filtering if needed, 
    # but accessing by key works on sqlite3.Row too.
    
    total = len(all_candidates)
    pending = len([c for c in all_candidates if c['status'] == 'pending'])
    completed = len([c for c in all_candidates if c['status'] != 'pending'])
    contacted = len([c for c in all_candidates if c['status'] == 'contacted'])
    not_interested = len([c for c in all_candidates if c['status'] == 'not_interested'])
    
    success_rate = 0
    if completed > 0:
        success_rate = int((contacted / completed) * 100)
    
    conn.close()
    
    return {
        'total': total,
        'pending': pending,
        'today': calls_today,
        'completed': completed,
        'interviewed': contacted,
        'rejected': not_interested,
        'success_rate': success_rate,
        'status_dist': [
            {'status': 'Pending', 'count': pending},
            {'status': 'Contacted', 'count': contacted},
            {'status': 'Not Interested', 'count': not_interested}
        ]
    }

def get_chart_data():
    conn = get_db_connection()
    
    # 1. Status Distribution
    status_counts = conn.execute('''
        SELECT status, COUNT(*) as count 
        FROM candidates 
        GROUP BY status
    ''').fetchall()
    
    # Format for Chart.js
    statuses = [row['status'].title() for row in status_counts]
    counts = [row['count'] for row in status_counts]
    
    # 2. Daily Activity (Last 7 Days)
    daily_calls = conn.execute('''
        SELECT DATE(call_time) as date, COUNT(*) as count 
        FROM call_logs 
        WHERE call_time >= DATE('now', '-7 days')
        GROUP BY DATE(call_time)
        ORDER BY date ASC
    ''').fetchall()
    
    dates = [row['date'] for row in daily_calls]
    call_counts = [row['count'] for row in daily_calls]
    
    conn.close()
    
    return {
        'status_labels': statuses,
        'status_data': counts,
        'activity_labels': dates,
        'activity_data': call_counts
    }

def get_daily_stats_report():
    conn = get_db_connection()
    stats = conn.execute('''
        SELECT DATE(call_time) as date, 
               COUNT(*) as total_calls,
               SUM(CASE WHEN outcome = 'contacted' THEN 1 ELSE 0 END) as contacted,
               SUM(CASE WHEN outcome = 'not_interested' THEN 1 ELSE 0 END) as not_interested
        FROM call_logs 
        WHERE call_time >= DATE('now', '-7 days')
        GROUP BY DATE(call_time)
        ORDER BY date DESC
    ''').fetchall()
    conn.close()
    return stats

def get_status_distribution():
    conn = get_db_connection()
    dist = conn.execute('''
        SELECT status, COUNT(*) as count 
        FROM candidates 
        GROUP BY status
    ''').fetchall()
    conn.close()
    return dist

def get_last_transcript(candidate_id):
    conn = get_db_connection()
    row = conn.execute('SELECT transcript FROM call_logs WHERE candidate_id = ? ORDER BY id DESC LIMIT 1', (candidate_id,)).fetchone()
    conn.close()
    return row['transcript'] if row else None
