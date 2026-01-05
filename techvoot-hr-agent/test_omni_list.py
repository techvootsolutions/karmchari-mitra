
from config import Config
from omnidimension import Client
import inspect

try:
    client = Client(Config.OMNIDIMENSION_API_KEY)
    print("Client initialized.")
    print("Methods in client.call:")
    print(dir(client.call))
    
    # Check explicitly if 'list' or 'get_calls' exists
    methods = [m for m in dir(client.call) if not m.startswith('_')]
    for m in methods:
        print(f" - {m}")
        
    # Attempt to list calls if a likely method exists
    if 'list_calls' in methods or 'list' in methods:
        method_name = 'list_calls' if 'list_calls' in methods else 'list'
        print(f"\nAttempting to call {method_name}...")
        method = getattr(client.call, method_name)
        try:
            # Try with clean args
            calls = method(limit=5)
            print(f"Success! Got {len(calls)} calls.")
            for c in calls:
                print(c)
        except Exception as e:
            print(f"Invocation failed: {e}")

except Exception as e:
    print(f"Error: {e}")
