
import sqlite3
import database

conn = database.get_db_connection()
conn.row_factory = sqlite3.Row

print("--- CANDIDATE DEBUG ---")
candidates = conn.execute("SELECT * FROM candidates WHERE name LIKE '%Hardik%'").fetchall()
for c in candidates:
    print(dict(c))
    cid = c['id']
    print(f"  Logs for Candidate {cid}:")
    logs = conn.execute("SELECT * FROM call_logs WHERE candidate_id = ?", (cid,)).fetchall()
    for l in logs:
        print("    ", dict(l))

conn.close()
