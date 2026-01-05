import database
import sqlite3

def check_assignments():
    conn = database.get_db_connection()
    logs = conn.execute('SELECT * FROM call_logs').fetchall()
    print(f"Total logs: {len(logs)}")
    for log in logs:
        print(f"ID: {log['id']}, Outcome: {log['outcome']}, External ID: {log['external_call_id']}")
    
    initiated = database.get_initiated_calls()
    print(f"Initiated calls (via get_initiated_calls): {len(initiated)}")
    conn.close()

if __name__ == "__main__":
    check_assignments()
