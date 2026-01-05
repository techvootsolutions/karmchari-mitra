
import database
import sheets_integration

def reimport():
    conn = database.get_db_connection()
    print("Clearing call_logs table...")
    conn.execute("DELETE FROM call_logs")
    conn.commit()
    conn.close()
    
    print("Re-importing from Sheets...")
    count = sheets_integration.import_from_sheets()
    print(f"Imported {count} rows.")

if __name__ == "__main__":
    reimport()
