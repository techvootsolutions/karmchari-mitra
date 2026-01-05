
import sqlite3

conn = sqlite3.connect('hr_candidates.db')
conn.row_factory = sqlite3.Row
try:
    # Check Schema
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(job_rules)")
    columns = cursor.fetchall()
    print("Job Rules Columns:")
    for col in columns:
        print(f" - {col[1]} ({col[2]})")
        
    # Check Content
    rows = conn.execute("SELECT * FROM job_rules").fetchall()
    print("\nExisting Rules:")
    for row in rows:
        print(dict(row))
        
except Exception as e:
    print(e)
finally:
    conn.close()
