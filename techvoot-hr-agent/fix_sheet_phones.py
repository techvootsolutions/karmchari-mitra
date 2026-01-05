
from config import Config
from sheets_integration import get_sheet
from omnidimension import Client
import gspread

def fix_phones():
    print("Connecting to Sheet...")
    sheet = get_sheet()
    if not sheet:
        print("Failed to connect.")
        return

    print("Connecting to API...")
    client = Client(Config.OMNIDIMENSION_API_KEY)

    records = sheet.get_all_records()
    print(f"Checking {len(records)} rows...")
    
    # We need row index to update (1-based, +1 for header)
    for i, r in enumerate(records):
        row_idx = i + 2
        call_id = str(r.get('call_id', ''))
        current_phone = str(r.get('phone_number', ''))
        
        # Check if phone looks like the bot number (ending in 288404)
        if '969288404' in current_phone or not current_phone:
            print(f"Row {row_idx}: Suspicious phone {current_phone} for ID {call_id}. Fetching API...")
            
            try:
                # Fetch log details
                # The API doesn't seem to have get_call_log(id)?
                # We have to List and filter, or hope get_call_logs(id=...) works?
                # Based on previous tests, we can only list.
                # So we list generic and find matching ID.
                # This is inefficient but fine for 6 rows.
                
                # Fetch a batch (assuming log is recent)
                resp = client.call.get_call_logs(page_size=50, agent_id=Config.OMNIDIMENSION_AGENT_ID)
                
                target_log = None
                if isinstance(resp, dict) and 'json' in resp:
                    resp = resp['json']
                if 'call_log_data' in resp:
                    for l in resp['call_log_data']:
                        if str(l.get('id')) == call_id or str(l.get('call_log_id')) == call_id:
                            target_log = l
                            break
                            
                if target_log:
                    real_phone = target_log.get('to_number')
                    print(f"  > Found real phone: {real_phone}")
                    
                    # Update Sheet (Col 3 is phone_number)
                    sheet.update_cell(row_idx, 3, real_phone)
                    print("  > Updated.")
                else:
                    print("  > Log not found in recent API calls.")
            except Exception as e:
                print(f"  > Error: {e}")

if __name__ == "__main__":
    fix_phones()
