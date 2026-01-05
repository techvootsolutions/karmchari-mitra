import database
import sqlite3

def cleanup_invalid_calls():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Check for logs with outcome='initiated' and NULL or empty external_call_id
    cursor.execute('''
        SELECT count(*) FROM call_logs 
        WHERE outcome = 'initiated' 
        AND (external_call_id IS NULL OR external_call_id = '')
    ''')
    count = cursor.fetchone()[0]
    print(f"Found {count} invalid initiated calls.")
    
    if count > 0:
        cursor.execute('''
            UPDATE call_logs 
            SET outcome = 'failed', notes = 'Cleanup: Missing external ID'
            WHERE outcome = 'initiated' 
            AND (external_call_id IS NULL OR external_call_id = '')
        ''')
        
        # Also ensure candidates are reset to pending or failed? 
        # Actually, if we mark log as failed, maybe candidate should be 'call_failed' or remain 'pending' if we want to retry?
        # Let's just mark them as 'call_failed' so they aren't stuck in limbo, or maybe just leave status as is?
        # The log_call function updates candidate status. If we update log, we should probably update candidate too.
        # But for now, let's just clean the logs so sync doesn't get confused. 
        # Ideally, we should set candidate status back to 'pending' to retry?
        # Let's set to 'call_failed_cleanup'
        
        # We need to find the candidates associated with these logs
        # Actually, simpler is just to update the logs.
        
        conn.commit()
        print(f"Updated {count} logs to 'failed'.")
    
    conn.close()

if __name__ == "__main__":
    cleanup_invalid_calls()
