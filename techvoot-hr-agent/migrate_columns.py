import sqlite3

def migrate_missing_columns():
    print("Migrating missing columns...")
    conn = sqlite3.connect('hr_candidates.db')
    cursor = conn.cursor()
    
    columns = ['transcript', 'recording_url']
    
    for col in columns:
        try:
            cursor.execute(f'ALTER TABLE call_logs ADD COLUMN {col} TEXT')
            print(f"Added {col} column.")
        except sqlite3.OperationalError as e:
            print(f"Column {col} likely exists: {e}")
            
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_missing_columns()
