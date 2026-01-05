
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Techvoot HR Data").sheet1
    records = sheet.get_all_records()
    
    print(f"Total Rows in Sheet: {len(records)}")
    
    print("\n--- SHEET HEADERS ---")
    headers = sheet.row_values(1)
    print(headers)

    print("\n--- SHEET DATA SAMPLE ---")
    for r in records:
        trans = str(r.get('full_conversation', ''))[:50]
        print(f"ID: {r.get('call_id')} | Name: {r.get('applicant_name')} | Trans: {trans}...")
            
    if not found:
        print("Hardik NOT found in sheet.")
    
except Exception as e:
    print(f"Error: {e}")
