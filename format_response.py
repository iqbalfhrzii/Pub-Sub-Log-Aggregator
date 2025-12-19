import json
import requests

def get_formatted_events():
    """Get events with formatted output"""
    response = requests.get("http://localhost:8081/events?limit=5")
    data = response.json()
    
    print("=== FORMATTED EVENT RESPONSE ===\n")
    print(f"Total Events: {data['count']}")
    print(f"Limit: {data['limit']}")
    print(f"Topic Filter: {data.get('topic_filter', 'None')}")
    print("\n" + "="*50)
    
    for i, event in enumerate(data['events'], 1):
        print(f"\n[{i}] EVENT:")
        print(f"  Topic: {event['topic']}")
        print(f"  Event ID: {event['event_id']}")
        print(f"  Source: {event['source']}")
        print(f"  Timestamp: {event['timestamp']}")
        print(f"  Processed At: {event['processed_at']}")
        print(f"  Action: {event['payload'].get('action', 'N/A')}")
        print(f"  User ID: {event['payload'].get('user_id', 'N/A')}")
        print(f"  Details: {event['payload'].get('details', 'N/A')[:50]}...")

def get_pretty_json():
    """Get events as pretty formatted JSON"""
    response = requests.get("http://localhost:8081/events?limit=3")
    data = response.json()
    
    print("=== PRETTY JSON RESPONSE ===\n")
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    get_formatted_events()
    print("\n" + "="*70 + "\n")
    get_pretty_json()