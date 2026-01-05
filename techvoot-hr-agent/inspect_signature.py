
from config import Config
from omnidimension import Client
import inspect

try:
    client = Client(Config.OMNIDIMENSION_API_KEY)
    print("Method: get_call_logs")
    sig = inspect.signature(client.call.get_call_logs)
    print(sig)
    
except Exception as e:
    print(f"Error: {e}")
