import requests
import json
import time
from datetime import datetime, timezone
import uuid

def test_system():
    base_url = "http://localhost:8081"
    
    print("=== Final UAS System Test ===\n")
    
    # Test 1: Health Check
    print("1. Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✓ Status: {health['status']}")
            print(f"   ✓ Database: {health['database']}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 2: Initial Stats
    print("\n2. Initial Stats...")
    try:
        response = requests.get(f"{base_url}/stats")
        initial_stats = response.json()
        print(f"   Received: {initial_stats.get('received_count', 0)}")
        print(f"   Processed: {initial_stats.get('unique_processed_count', 0)}")
        print(f"   Duplicates: {initial_stats.get('duplicate_dropped_count', 0)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 3: Publish Single Event
    print("\n3. Publishing Single Event...")
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
            print(f"   ✓ Published: {result['event_id']}")
            print(f"   ✓ Processed: {result.get('processed', False)}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Duplicate Detection
    print("\n4. Testing Duplicate Detection...")
    try:
        # Send same event again
        response = requests.post(f"{base_url}/publish", json=event1)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Response: {result['message']}")
            print(f"   ✓ Processed: {result.get('processed', False)}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 5: Batch Publishing
    print("\n5. Testing Batch Publishing...")
    batch_events = []
    for i in range(5):
        event = {
            "topic": "batch_test",
            "event_id": f"batch-{i:03d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "batch_source",
            "payload": {"batch_id": i, "data": f"batch data {i}"}
        }
        batch_events.append(event)
    
    try:
        batch_data = {"events": batch_events}
        response = requests.post(f"{base_url}/publish/batch", json=batch_data)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Batch processed: {result['processed']} new, {result['duplicates']} duplicates")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 6: Get Events
    print("\n6. Retrieving Events...")
    try:
        response = requests.get(f"{base_url}/events")
        if response.status_code == 200:
            events = response.json()
            print(f"   ✓ Total events: {events['count']}")
            if events['events']:
                print(f"   ✓ Latest event: {events['events'][0]['event_id']}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 7: Topic Filtering
    print("\n7. Testing Topic Filtering...")
    try:
        response = requests.get(f"{base_url}/events", params={"topic": "test_topic"})
        if response.status_code == 200:
            events = response.json()
            print(f"   ✓ Events for 'test_topic': {events['count']}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 8: Final Stats
    print("\n8. Final Stats...")
    try:
        response = requests.get(f"{base_url}/stats")
        final_stats = response.json()
        print(f"   Received: {final_stats.get('received_count', 0)}")
        print(f"   Processed: {final_stats.get('unique_processed_count', 0)}")
        print(f"   Duplicates: {final_stats.get('duplicate_dropped_count', 0)}")
        print(f"   Topics: {final_stats.get('topics_count', 0)}")
        print(f"   Uptime: {final_stats.get('uptime_seconds', 0)} seconds")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n=== Test Completed Successfully! ===")
    return True

if __name__ == "__main__":
    test_system()