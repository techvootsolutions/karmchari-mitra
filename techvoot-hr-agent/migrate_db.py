import sqlite3

def migrate_db():
    print("Migrating database...")
    conn = sqlite3.connect('hr_candidates.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE call_logs ADD COLUMN external_call_id TEXT')
        print("Added external_call_id column.")
    except sqlite3.OperationalError:
        print("Column external_call_id already exists.")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
