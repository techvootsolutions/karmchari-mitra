
import sqlite3
import database

# 1. Create Dummy
cid = database.add_new_candidate("Test Delete", "9999999999", "test@test.com", "Tester")
print(f"Created Candidate: {cid}")

# 2. Add Log
database.log_call(cid, "completed", 120, "Test Note", external_call_id="TEST_CALL_123")
print("Added Log")

# 3. Check Dashboard
conn = database.get_db_connection()
calls = conn.execute('''
    SELECT c.id, c.name
    FROM call_logs l
    JOIN candidates c ON l.candidate_id = c.id
    WHERE l.outcome != 'pending' 
''').fetchall()
conn.close()

found = False
for call in calls:
    if call['id'] == cid:
        found = True
        print("Found in Dashboard Query: YES")

# 4. Delete
print("Deleting...")
database.delete_candidate(cid)

# 5. Check Dashboard Again
conn = database.get_db_connection()
calls = conn.execute('''
    SELECT c.id, c.name
    FROM call_logs l
    JOIN candidates c ON l.candidate_id = c.id
    WHERE l.outcome != 'pending' 
''').fetchall()
conn.close()

found_after = False
for call in calls:
    if call['id'] == cid:
        found_after = True

print(f"Found in Dashboard Query After Delete: {found_after}")

if not found_after:
    print("SUCCESS: Entry removed.")
else:
    print("FAILURE: Entry still exists.")
