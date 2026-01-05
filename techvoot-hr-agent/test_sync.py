
import sheets_integration
import database

print("--- TESTING FULL SYNC CYCLE ---")

# 1. Export (Fetch from API -> Sheet)
print("1. Exporting from API to Sheet...")
try:
    count_export = sheets_integration.export_to_sheets()
    print(f"   Exported {count_export} new rows.")
except Exception as e:
    print(f"   EXPORT FAILED: {e}")

# 2. Import (Sheet -> DB)
print("2. Importing from Sheet to Database...")
try:
    count_import = sheets_integration.import_from_sheets()
    print(f"   Imported {count_import} rows.")
except Exception as e:
    print(f"   IMPORT FAILED: {e}")
    
# 3. Check for specific user if needed (Hardik)
print("3. Checking for Hardik...")
conn = database.get_db_connection()
c = conn.execute("SELECT * FROM candidates WHERE name LIKE '%Hardik%'").fetchone()
if c:
    print(f"   Hardik Found! Status: {c['status']}")
    logs = conn.execute("SELECT * FROM call_logs WHERE candidate_id = ?", (c['id'],)).fetchall()
    print(f"   Call Logs: {len(logs)}")
else:
    print("   Hardik still missing from DB.")
conn.close()
