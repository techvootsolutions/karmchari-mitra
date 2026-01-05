from omnidimension import Client
from config import Config
import inspect

def inspect_client():
    try:
        client = Client(Config.OMNIDIMENSION_API_KEY)
        print("\n--- client.call Attributes ---")
        print(dir(client.call))
        
        # Check for potential retrieval methods
        candidates = ['get', 'retrieve', 'list', 'get_details', 'get_call', 'history']
        
        print("\n--- Methods Inspection ---")
        for attr in dir(client.call):
            if not attr.startswith('_'):
                method = getattr(client.call, attr)
                print(f"\nMethod: {attr}")
                print(f"Signature: {inspect.signature(method) if callable(method) else 'Not callable'}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_client()
