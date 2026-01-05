import gspread
from oauth2client.service_account import ServiceAccountCredentials
from omnidimension import Client
from config import Config
import database
import sys

def test_integration():
    print("--- 1. Testing Google Sheets Connection ---")
    try:
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Techvoot HR Data").sheet1
        print("✅ Success: Acessed Sheet 'Techvoot HR Data'")
    except Exception as e:
        print(f"❌ Failed to access Google Sheet: {e}")
        return

    print("\n--- 2. Testing Omnidimension API ---")
    try:
        omni_client = Client(Config.OMNIDIMENSION_API_KEY)
        print(f"Using API Key: {Config.OMNIDIMENSION_API_KEY[:5]}...")
    except Exception as e:
        print(f"❌ Client Init Failed: {e}")
        return

    print("\n--- 3. Testing Data Fetch ---")
    conn = database.get_db_connection()
    log = conn.execute('SELECT * FROM call_logs WHERE external_call_id IS NOT NULL ORDER BY call_time DESC LIMIT 1').fetchone()
    conn.close()

    if not log:
        print("⚠️ No call logs found in local database with external_call_id.")
        return

    external_id = log['external_call_id']
    print(f"Found local log with ID: {external_id}")
    
    try:
        details = omni_client.call.get_call_log(call_log_id=external_id)
        if hasattr(details, 'id'):
            print("✅ Success: Fetched call details from Omnidimension.")
        else:
            print("✅ Success (Dict): Fetched call details.")
    except Exception as e:
        print(f"❌ Failed to fetch call details: {e}")
        print("Reason: You changed the API Key, but the call log ID belongs to the OLD account.")

if __name__ == "__main__":
    test_integration()
