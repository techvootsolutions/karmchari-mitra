
from sheets_integration import get_sheet
import time

def cleanup_sheet():
    print("Connecting to Sheet...")
    sheet = get_sheet()
    
    # IDs to remove to force re-export
    target_ids = ['774726', '774727', '774756', '774757']
    
    records = sheet.get_all_records()
    print(f"Total rows: {len(records)}")
    
    # Iterate backwards to delete safely
    for i in range(len(records) - 1, -1, -1):
        r = records[i]
        call_id = str(r.get('call_id', ''))
        
        if call_id in target_ids:
            row_idx = i + 2 # +1 for header, +1 for 1-based index
            print(f"Deleting Row {row_idx} (ID: {call_id})...")
            sheet.delete_rows(row_idx)
            time.sleep(1) # Rate limit safety

if __name__ == "__main__":
    cleanup_sheet()
