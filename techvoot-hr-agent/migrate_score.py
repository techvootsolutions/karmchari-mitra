import sqlite3

def migrate_score():
    print("Adding score and analysis to call_logs...")
    conn = sqlite3.connect('hr_candidates.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE call_logs ADD COLUMN score INTEGER DEFAULT 0')
        print("Added score column.")
    except sqlite3.OperationalError:
        print("Column score already exists.")

    try:
        cursor.execute('ALTER TABLE call_logs ADD COLUMN analysis TEXT')
        print("Added analysis column.")
    except sqlite3.OperationalError:
        print("Column analysis already exists.")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_score()
