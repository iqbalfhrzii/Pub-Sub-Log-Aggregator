import requests
import time
import json
from datetime import datetime, timezone

def debug_system():
    base_url = "http://localhost:8080"
    
    print("=== Debugging UAS System ===\n")
    
    # 1. Check health
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            health = response.json()
            print(f"  Database: {health.get('database')}")
            print(f"  Redis: {health.get('redis')}")
        print()
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # 2. Check initial stats
    try:
        response = requests.get(f"{base_url}/stats")
        initial_stats = response.json()
        print("Initial Stats:")
        print(f"  Received: {initial_stats.get('received_count', 0)}")
        print(f"  Processed: {initial_stats.get('unique_processed_count', 0)}")
        print(f"  Duplicates: {initial_stats.get('duplicate_dropped_count', 0)}")
        print(f"  Queue Length: {initial_stats.get('queue_length', 0)}")
        print()
    except Exception as e:
        print(f"Stats check failed: {e}")
        return
    
    # 3. Send a test event
    test_event = {
        "topic": "debug_test",
        "event_id": "debug-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "debug_source",
        "payload": {"debug": True, "message": "test event"}
    }
    
    print("Sending test event...")
    try:
        response = requests.post(f"{base_url}/publish", json=test_event)
        print(f"Publish Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"  Response: {result}")
        else:
            print(f"  Error: {response.text}")
        print()
    except Exception as e:
        print(f"Publish failed: {e}")
        return
    
    # 4. Wait and check stats again
    print("Waiting 5 seconds for processing...")
    time.sleep(5)
    
    try:
        response = requests.get(f"{base_url}/stats")
        final_stats = response.json()
        print("Final Stats:")
        print(f"  Received: {final_stats.get('received_count', 0)}")
        print(f"  Processed: {final_stats.get('unique_processed_count', 0)}")
        print(f"  Duplicates: {final_stats.get('duplicate_dropped_count', 0)}")
        print(f"  Queue Length: {final_stats.get('queue_length', 0)}")
        print()
        
        # Check if processing happened
        if final_stats.get('received_count', 0) > initial_stats.get('received_count', 0):
            print("[OK] Event was received")
        else:
            print("[ERROR] Event was not received")
            
        if final_stats.get('unique_processed_count', 0) > initial_stats.get('unique_processed_count', 0):
            print("[OK] Event was processed")
        else:
            print("[ERROR] Event was not processed")
            
    except Exception as e:
        print(f"Final stats check failed: {e}")
    
    # 5. Check events endpoint
    print("\nChecking events endpoint...")
    try:
        response = requests.get(f"{base_url}/events")
        if response.status_code == 200:
            events = response.json()
            print(f"Total events retrieved: {events.get('count', 0)}")
            if events.get('events'):
                print("Latest events:")
                for event in events['events'][:3]:
                    print(f"  - {event.get('topic')}/{event.get('event_id')}")
        else:
            print(f"Events endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"Events check failed: {e}")

if __name__ == "__main__":
    debug_system()