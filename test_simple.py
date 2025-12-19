import requests
import json
import time
from datetime import datetime, timezone

def test_system():
    base_url = "http://localhost:8081"
    
    print("=== UAS System Test ===\n")
    
    # Test 1: Health Check
    print("1. Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"   [OK] Status: {health['status']}")
            print(f"   [OK] Database: {health['database']}")
        else:
            print(f"   [ERROR] Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        return False
    
    # Test 2: Publish Single Event
    print("\n2. Publishing Single Event...")
    event1 = {
        "topic": "test_topic",
        "event_id": "test-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test_source",
        "payload": {"message": "Hello World", "test": True}
    }
    
    try:
        response = requests.post(f"{base_url}/publish", json=event1)
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Published: {result['event_id']}")
            print(f"   [OK] Processed: {result.get('processed', False)}")
        else:
            print(f"   [ERROR] Failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    # Test 3: Duplicate Detection
    print("\n3. Testing Duplicate Detection...")
    try:
        response = requests.post(f"{base_url}/publish", json=event1)
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Response: {result['message']}")
            print(f"   [OK] Processed: {result.get('processed', False)}")
        else:
            print(f"   [ERROR] Failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    # Test 4: Get Events
    print("\n4. Retrieving Events...")
    try:
        response = requests.get(f"{base_url}/events")
        if response.status_code == 200:
            events = response.json()
            print(f"   [OK] Total events: {events['count']}")
            if events['events']:
                print(f"   [OK] Latest event: {events['events'][0]['event_id']}")
        else:
            print(f"   [ERROR] Failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    # Test 5: Stats
    print("\n5. System Stats...")
    try:
        response = requests.get(f"{base_url}/stats")
        stats = response.json()
        print(f"   Received: {stats.get('received_count', 0)}")
        print(f"   Processed: {stats.get('unique_processed_count', 0)}")
        print(f"   Duplicates: {stats.get('duplicate_dropped_count', 0)}")
        print(f"   Topics: {stats.get('topics_count', 0)}")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    print("\n=== Test Completed ===")
    return True

if __name__ == "__main__":
    test_system()