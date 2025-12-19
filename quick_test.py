import requests
import json
import time
from datetime import datetime, timezone

def test_system():
    base_url = "http://localhost:8080"
    
    print("=== Testing UAS Pub-Sub Aggregator ===\n")
    
    # Test 1: Health Check
    print("1. Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("[OK] Health check passed")
            print(f"    Response: {response.json()}")
        else:
            print(f"[ERROR] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return False
    
    print()
    
    # Test 2: Publish Single Event
    print("2. Testing Single Event Publish...")
    event = {
        "topic": "test_topic",
        "event_id": "test-event-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test_source",
        "payload": {"message": "Hello World", "test": True}
    }
    
    try:
        response = requests.post(f"{base_url}/publish", json=event, timeout=10)
        if response.status_code == 200:
            print("[OK] Event published successfully")
            print(f"    Response: {response.json()}")
        else:
            print(f"[ERROR] Event publish failed: {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Event publish failed: {e}")
    
    print()
    
    # Wait for processing
    print("3. Waiting for event processing...")
    time.sleep(3)
    
    # Test 3: Get Stats
    print("4. Testing Stats Endpoint...")
    try:
        response = requests.get(f"{base_url}/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print("[OK] Stats retrieved successfully")
            print(f"    Received: {stats.get('received_count', 0)}")
            print(f"    Processed: {stats.get('unique_processed_count', 0)}")
            print(f"    Duplicates: {stats.get('duplicate_dropped_count', 0)}")
            print(f"    Topics: {stats.get('topics_count', 0)}")
        else:
            print(f"[ERROR] Stats failed: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Stats failed: {e}")
    
    print()
    
    # Test 4: Get Events
    print("5. Testing Get Events...")
    try:
        response = requests.get(f"{base_url}/events", timeout=10)
        if response.status_code == 200:
            events = response.json()
            print(f"[OK] Retrieved {events.get('count', 0)} events")
            if events.get('events'):
                print(f"    Latest event: {events['events'][0]['event_id']}")
        else:
            print(f"[ERROR] Get events failed: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Get events failed: {e}")
    
    print()
    
    # Test 5: Duplicate Detection
    print("6. Testing Duplicate Detection...")
    try:
        # Send same event again
        response = requests.post(f"{base_url}/publish", json=event, timeout=10)
        if response.status_code == 200:
            print("[OK] Duplicate event sent")
            
            time.sleep(2)
            
            # Check stats again
            response = requests.get(f"{base_url}/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                print(f"[OK] After duplicate - Duplicates: {stats.get('duplicate_dropped_count', 0)}")
            
        else:
            print(f"[ERROR] Duplicate test failed: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Duplicate test failed: {e}")
    
    print("\n=== Test Completed ===")
    return True

if __name__ == "__main__":
    test_system()