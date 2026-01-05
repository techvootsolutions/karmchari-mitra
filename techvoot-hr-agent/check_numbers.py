
from config import Config
from omnidimension import Client
import json

client = Client(Config.OMNIDIMENSION_API_KEY)
resp = client.call.get_call_logs(page_size=5, agent_id=Config.OMNIDIMENSION_AGENT_ID)

if isinstance(resp, dict):
    data = []
    if 'json' in resp:
        resp = resp['json']
        
    if 'call_log_data' in resp:
        data = resp['call_log_data']
    
    print(f"Found {len(data)} logs.")
    for l in data:
        print(f"ID: {l.get('id')}")
        print(f"  Direction: {l.get('call_direction')}")
        print(f"  From: {l.get('from_number')}")
        print(f"  To:   {l.get('to_number')}")
        print("-" * 20)
else:
    print(f"Unexpected format: {type(resp)}")
