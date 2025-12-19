import requests
import json
import time
from datetime import datetime, timezone
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_comprehensive():
    base_url = "http://localhost:8081"
    
    print("=== Comprehensive UAS System Test ===\n")
    
    # Test 1: Basic Functionality
    print("1. Basic Functionality Test...")
    
    # Health check
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200
    print("   [OK] Health check passed")
    
    # Initial stats
    initial_stats = requests.get(f"{base_url}/stats").json()
    print(f"   [OK] Initial stats: {initial_stats['unique_processed_count']} processed")
    
    # Test 2: Single Event Publishing
    print("\n2. Single Event Publishing...")
    
    # Generate unique event ID for each test run
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    event = {
        "topic": "comprehensive_test",
        "event_id": f"comp-{unique_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test_source",
        "payload": {"test": "comprehensive", "number": 1}
    }
    
    response = requests.post(f"{base_url}/publish", json=event)
    assert response.status_code == 200
    result = response.json()
    assert result['processed'] == True
    print("   [OK] Single event published and processed")
    
    # Test 3: Duplicate Detection
    print("\n3. Duplicate Detection Test...")
    
    # Send same event again
    response = requests.post(f"{base_url}/publish", json=event)
    assert response.status_code == 200
    result = response.json()
    assert result['processed'] == False
    print("   [OK] Duplicate detected and rejected")
    
    # Test 4: Batch Publishing
    print("\n4. Batch Publishing Test...")
    
    batch_events = []
    for i in range(5):
        batch_event = {
            "topic": "batch_test",
            "event_id": f"batch-{i:03d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "batch_source",
            "payload": {"batch_number": i, "data": f"batch data {i}"}
        }
        batch_events.append(batch_event)
    
    batch_data = {"events": batch_events}
    response = requests.post(f"{base_url}/publish/batch", json=batch_data)
    assert response.status_code == 200
    result = response.json()
    assert result['processed'] == 5
    assert result['duplicates'] == 0
    print(f"   [OK] Batch processed: {result['processed']} new, {result['duplicates']} duplicates")
    
    # Test 5: Mixed Batch (with duplicates)
    print("\n5. Mixed Batch Test...")
    
    # Create mixed batch: 2 duplicates + 3 new
    mixed_events = batch_events[:2]  # 2 duplicates
    for i in range(3):
        new_event = {
            "topic": "mixed_test",
            "event_id": f"mixed-{i:03d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "mixed_source",
            "payload": {"mixed_number": i}
        }
        mixed_events.append(new_event)
    
    mixed_data = {"events": mixed_events}
    response = requests.post(f"{base_url}/publish/batch", json=mixed_data)
    assert response.status_code == 200
    result = response.json()
    assert result['processed'] == 3  # 3 new events
    assert result['duplicates'] == 2  # 2 duplicates
    print(f"   [OK] Mixed batch: {result['processed']} new, {result['duplicates']} duplicates")
    
    # Test 6: Concurrent Processing
    print("\n6. Concurrent Processing Test...")
    
    def send_event(event_id):
        event = {
            "topic": "concurrent_test",
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "concurrent_source",
            "payload": {"concurrent_id": event_id}
        }
        try:
            response = requests.post(f"{base_url}/publish", json=event, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    # Send 10 events concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_event, f"concurrent-{i:03d}") for i in range(10)]
        results = [future.result() for future in as_completed(futures)]
    
    success_count = sum(results)
    print(f"   [OK] Concurrent processing: {success_count}/10 events successful")
    
    # Test 7: Data Retrieval
    print("\n7. Data Retrieval Test...")
    
    # Get all events
    response = requests.get(f"{base_url}/events")
    assert response.status_code == 200
    all_events = response.json()
    print(f"   [OK] Total events retrieved: {all_events['count']}")
    
    # Get events by topic
    response = requests.get(f"{base_url}/events", params={"topic": "comprehensive_test"})
    assert response.status_code == 200
    topic_events = response.json()
    assert topic_events['count'] >= 1
    print(f"   [OK] Topic filtering: {topic_events['count']} events for 'comprehensive_test'")
    
    # Test 8: Final Statistics
    print("\n8. Final Statistics...")
    
    final_stats = requests.get(f"{base_url}/stats").json()
    
    print(f"   Total Received: {final_stats['received_count']}")
    print(f"   Unique Processed: {final_stats['unique_processed_count']}")
    print(f"   Duplicates Dropped: {final_stats['duplicate_dropped_count']}")
    print(f"   Topics Count: {final_stats['topics_count']}")
    print(f"   Uptime: {final_stats['uptime_seconds']} seconds")
    
    # Verify stats consistency
    total_events = final_stats['unique_processed_count'] + final_stats['duplicate_dropped_count']
    assert final_stats['received_count'] == total_events
    print("   [OK] Statistics are consistent")
    
    print("\n=== All Tests Passed Successfully! ===")
    
    # Performance summary
    processed_increase = final_stats['unique_processed_count'] - initial_stats['unique_processed_count']
    print(f"\nPerformance Summary:")
    print(f"- Events processed in this test: {processed_increase}")
    print(f"- Duplicates detected: {final_stats['duplicate_dropped_count'] - initial_stats.get('duplicate_dropped_count', 0)}")
    print(f"- Topics created: {final_stats['topics_count'] - initial_stats.get('topics_count', 0)}")
    
    return True

if __name__ == "__main__":
    try:
        test_comprehensive()
        print("\n[SUCCESS] All comprehensive tests completed!")
    except AssertionError as e:
        print(f"\n[FAILED] Test assertion failed: {e}")
    except Exception as e:
        print(f"\n[ERROR] Test error: {e}")