import requests
import json
from datetime import datetime, timezone

def debug_duplicate():
    base_url = "http://localhost:8081"
    
    print("=== Debug Duplicate Detection ===\n")
    
    # Create a test event
    event = {
        "topic": "debug_duplicate",
        "event_id": "debug-dup-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "debug_source",
        "payload": {"debug": True, "message": "duplicate test"}
    }
    
    print("1. Sending first event...")
    response1 = requests.post(f"{base_url}/publish", json=event)
    print(f"   Status: {response1.status_code}")
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"   Response: {result1}")
    else:
        print(f"   Error: {response1.text}")
        return
    
    print("\n2. Sending same event again (should be duplicate)...")
    response2 = requests.post(f"{base_url}/publish", json=event)
    print(f"   Status: {response2.status_code}")
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"   Response: {result2}")
    else:
        print(f"   Error: {response2.text}")
    
    print("\n3. Checking stats...")
    stats = requests.get(f"{base_url}/stats").json()
    print(f"   Received: {stats['received_count']}")
    print(f"   Processed: {stats['unique_processed_count']}")
    print(f"   Duplicates: {stats['duplicate_dropped_count']}")

if __name__ == "__main__":
    debug_duplicate()