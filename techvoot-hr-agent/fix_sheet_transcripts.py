
from config import Config
from sheets_integration import get_sheet
from omnidimension import Client
import gspread

def fix_transcripts():
    print("Connecting to Sheet...")
    sheet = get_sheet()
    if not sheet:
        print("Failed to connect.")
        return

    print("Connecting to API...")
    client = Client(Config.OMNIDIMENSION_API_KEY)

    # Find Transcript Column
    headers = sheet.row_values(1)
    try:
        col_idx = headers.index('full_conversation') + 1
    except ValueError:
        print("Header 'full_conversation' not found.")
        return

    records = sheet.get_all_records()
    print(f"Checking {len(records)} rows...")
    
    for i, r in enumerate(records):
        row_idx = i + 2
        call_id = str(r.get('call_id', ''))
        transcript = r.get('full_conversation', '')
        
        if not transcript or len(transcript) < 10:
            print(f"Row {row_idx}: Missing transcript for ID {call_id}. Fetching API...")
            
            try:
                # Fetch recent logs to find match
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
                    # Key might be 'call_conversation' or 'transcript'
                    real_transcript = target_log.get('call_conversation') or target_log.get('transcript') or "No Transcript Available"
                    
                    if real_transcript:
                        # Truncate if too huge? Sheets limit is 50k chars.
                        if len(real_transcript) > 49000:
                            real_transcript = real_transcript[:49000] + "..."
                            
                        sheet.update_cell(row_idx, col_idx, real_transcript)
                        print(f"  > Updated ({len(real_transcript)} chars).")
                    else:
                        print("  > Transcript empty in API.")
                else:
                    print("  > Log not found in recent API calls.")
            except Exception as e:
                print(f"  > Error: {e}")

if __name__ == "__main__":
    fix_transcripts()
