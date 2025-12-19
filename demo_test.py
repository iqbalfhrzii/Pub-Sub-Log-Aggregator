import requests
import json
import time
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

def demo_test():
    base_url = "http://localhost:8081"
    
    print("=== UAS Demo Test ===\n")
    
    # Generate unique IDs for this test run
    test_id = str(uuid.uuid4())[:8]
    
    # Test 1: Health Check
    print("1. Health Check...")
    response = requests.get(f"{base_url}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test 2: Initial Stats
    print("\n2. Initial Stats...")
    initial_stats = requests.get(f"{base_url}/stats").json()
    print(f"   Processed: {initial_stats['unique_processed_count']}")
    print(f"   Duplicates: {initial_stats['duplicate_dropped_count']}")
    
    # Test 3: Single Event
    print(f"\n3. Single Event (ID: {test_id})...")
    event = {
        "topic": "demo_test",
        "event_id": f"demo-{test_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "demo_source",
        "payload": {"demo": True, "test_id": test_id}
    }
    
    response = requests.post(f"{base_url}/publish", json=event)
    result = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Processed: {result.get('processed', 'N/A')}")
    print(f"   Message: {result.get('message', 'N/A')}")
    
    # Test 4: Duplicate Event
    print("\n4. Duplicate Event (same ID)...")
    response = requests.post(f"{base_url}/publish", json=event)
    result = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Processed: {result.get('processed', 'N/A')}")
    print(f"   Message: {result.get('message', 'N/A')}")
    
    # Test 5: Concurrent Events
    print("\n5. Concurrent Events...")
    
    def send_concurrent_event(i):
        event = {
            "topic": "concurrent_demo",
            "event_id": f"concurrent-{test_id}-{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "concurrent_source",
            "payload": {"index": i, "test_id": test_id}
        }
        response = requests.post(f"{base_url}/publish", json=event)
        return response.status_code == 200
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_concurrent_event, i) for i in range(5)]
        results = [f.result() for f in futures]
    
    print(f"   Success: {sum(results)}/5 events")
    
    # Test 6: Final Stats
    print("\n6. Final Stats...")
    final_stats = requests.get(f"{base_url}/stats").json()
    print(f"   Processed: {final_stats['unique_processed_count']}")
    print(f"   Duplicates: {final_stats['duplicate_dropped_count']}")
    print(f"   Topics: {final_stats['topics_count']}")
    
    # Calculate changes
    new_processed = final_stats['unique_processed_count'] - initial_stats['unique_processed_count']
    new_duplicates = final_stats['duplicate_dropped_count'] - initial_stats['duplicate_dropped_count']
    
    print(f"\n=== Test Summary ===")
    print(f"New events processed: {new_processed}")
    print(f"New duplicates detected: {new_duplicates}")
    print(f"Test ID: {test_id}")

if __name__ == "__main__":
    demo_test()