
import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('hr_candidates.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(call_logs)")
        columns = [c[1] for c in cursor.fetchall()]
        
        if 'interaction_count' not in columns:
            print("Adding interaction_count column...")
            cursor.execute("ALTER TABLE call_logs ADD COLUMN interaction_count INTEGER DEFAULT 0")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column interaction_count already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
