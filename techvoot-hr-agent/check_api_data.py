
from config import Config
from omnidimension import Client
import json

try:
    print("Initializing client...")
    client = Client(Config.OMNIDIMENSION_API_KEY)
    
    print("Fetching logs...")
    resp = client.call.get_call_logs(page_size=10, agent_id=Config.OMNIDIMENSION_AGENT_ID)
    
    if hasattr(resp, 'json'):
        print("Response has .json attr")
    
    if isinstance(resp, dict):
        print(f"Keys: {resp.keys()}")
        if 'call_log_data' in resp:
            data = resp['call_log_data']
            print(f"Count: {len(data)}")
            if len(data) > 0:
                print("First Log Keys:", data[0].keys())
                for l in data:
                    print(f"ID: {l.get('id')} / {l.get('call_log_id')} | Created: {l.get('created_at')}")
    else:
        print(f"Type: {type(resp)}")

except Exception as e:
    print(f"Error: {e}")
