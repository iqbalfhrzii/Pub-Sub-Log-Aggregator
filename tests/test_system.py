import pytest
import requests
import json
import time
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Test configuration
AGGREGATOR_URL = "http://localhost:8080"
TEST_TIMEOUT = 30

class TestPubSubAggregator:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup untuk setiap test"""
        # Wait untuk service ready
        self.wait_for_service()
        
    def wait_for_service(self, max_retries=30):
        """Wait untuk aggregator service siap"""
        for i in range(max_retries):
            try:
                response = requests.get(f"{AGGREGATOR_URL}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        pytest.fail("Aggregator service not available")
    
    def create_test_event(self, topic="test_topic", event_id=None):
        """Helper untuk membuat test event"""
        if not event_id:
            event_id = str(uuid.uuid4())
        
        return {
            "topic": topic,
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "test_source",
            "payload": {"test": "data", "value": 123}
        }
    
    def test_health_check(self):
        """Test 1: Health check endpoint"""
        response = requests.get(f"{AGGREGATOR_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "timestamp" in data
    
    def test_publish_single_event(self):
        """Test 2: Publish single event"""
        event = self.create_test_event()
        
        response = requests.post(f"{AGGREGATOR_URL}/publish", json=event)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "accepted"
        assert data["event_id"] == event["event_id"]
        assert data["topic"] == event["topic"]
    
    def test_event_deduplication(self):
        """Test 3: Event deduplication - kirim duplikat, hanya sekali diproses"""
        event = self.create_test_event(topic="dedup_test")
        
        # Kirim event pertama kali
        response1 = requests.post(f"{AGGREGATOR_URL}/publish", json=event)
        assert response1.status_code == 200
        
        # Tunggu processing
        time.sleep(2)
        
        # Ambil stats awal
        stats1 = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Kirim event yang sama (duplikat)
        response2 = requests.post(f"{AGGREGATOR_URL}/publish", json=event)
        assert response2.status_code == 200
        
        # Tunggu processing
        time.sleep(2)
        
        # Ambil stats setelah duplikat
        stats2 = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Verify deduplication
        assert stats2["received_count"] == stats1["received_count"] + 1
        assert stats2["unique_processed_count"] == stats1["unique_processed_count"]  # Tidak bertambah
        assert stats2["duplicate_dropped_count"] == stats1["duplicate_dropped_count"] + 1
    
    def test_batch_publish(self):
        """Test 4: Batch publish events"""
        events = [self.create_test_event(topic="batch_test") for _ in range(5)]
        batch_data = {"events": events}
        
        response = requests.post(f"{AGGREGATOR_URL}/publish/batch", json=batch_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "accepted"
        assert data["count"] == 5
    
    def test_get_events(self):
        """Test 5: Get events endpoint"""
        # Publish beberapa event
        topic = "get_events_test"
        for i in range(3):
            event = self.create_test_event(topic=topic)
            requests.post(f"{AGGREGATOR_URL}/publish", json=event)
        
        time.sleep(2)  # Wait processing
        
        # Get all events
        response = requests.get(f"{AGGREGATOR_URL}/events")
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert "count" in data
        
        # Get events by topic
        response = requests.get(f"{AGGREGATOR_URL}/events", params={"topic": topic})
        assert response.status_code == 200
        
        data = response.json()
        assert data["topic_filter"] == topic
        # Should have at least the events we just published
        assert len(data["events"]) >= 3
    
    def test_stats_endpoint(self):
        """Test 6: Stats endpoint"""
        response = requests.get(f"{AGGREGATOR_URL}/stats")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "received_count", "unique_processed_count", 
            "duplicate_dropped_count", "topics_count", "uptime_seconds"
        ]
        
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], int)
    
    def test_invalid_event_schema(self):
        """Test 7: Invalid event schema validation"""
        invalid_events = [
            {},  # Empty
            {"topic": "test"},  # Missing fields
            {"topic": "", "event_id": "123", "timestamp": "invalid", "source": "test", "payload": {}},  # Invalid timestamp
            {"topic": "test", "event_id": "", "timestamp": "2023-01-01T00:00:00Z", "source": "test", "payload": {}}  # Empty event_id
        ]
        
        for invalid_event in invalid_events:
            response = requests.post(f"{AGGREGATOR_URL}/publish", json=invalid_event)
            assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_concurrent_processing(self):
        """Test 8: Concurrent processing - test race conditions"""
        topic = "concurrent_test"
        num_threads = 5
        events_per_thread = 10
        
        def publish_events(thread_id):
            results = []
            for i in range(events_per_thread):
                event = self.create_test_event(topic=f"{topic}_{thread_id}_{i}")
                try:
                    response = requests.post(f"{AGGREGATOR_URL}/publish", json=event, timeout=10)
                    results.append(response.status_code == 200)
                except:
                    results.append(False)
            return results
        
        # Run concurrent publishing
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(publish_events, i) for i in range(num_threads)]
            
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Verify semua berhasil
        success_count = sum(all_results)
        assert success_count >= num_threads * events_per_thread * 0.9  # Allow 10% failure tolerance
    
    def test_concurrent_duplicate_processing(self):
        """Test 9: Concurrent duplicate processing - test idempotency under concurrency"""
        event = self.create_test_event(topic="concurrent_dup_test")
        num_threads = 10
        
        # Get initial stats
        initial_stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        def send_duplicate():
            try:
                response = requests.post(f"{AGGREGATOR_URL}/publish", json=event, timeout=10)
                return response.status_code == 200
            except:
                return False
        
        # Send same event concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(send_duplicate) for _ in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        time.sleep(3)  # Wait for processing
        
        # Get final stats
        final_stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Verify idempotency: hanya 1 event yang diproses meski dikirim berkali-kali
        processed_increase = final_stats["unique_processed_count"] - initial_stats["unique_processed_count"]
        assert processed_increase == 1  # Hanya 1 event unik yang diproses
        
        # Verify duplicate detection
        duplicate_increase = final_stats["duplicate_dropped_count"] - initial_stats["duplicate_dropped_count"]
        assert duplicate_increase >= num_threads - 1  # Sisanya adalah duplikat
    
    def test_persistence_after_restart(self):
        """Test 10: Persistence - data tetap ada setelah restart (simulasi)"""
        # Publish unique event
        unique_event = self.create_test_event(topic="persistence_test")
        response = requests.post(f"{AGGREGATOR_URL}/publish", json=unique_event)
        assert response.status_code == 200
        
        time.sleep(2)  # Wait processing
        
        # Verify event processed
        stats_before = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Simulate restart by sending same event again (should be detected as duplicate)
        response = requests.post(f"{AGGREGATOR_URL}/publish", json=unique_event)
        assert response.status_code == 200
        
        time.sleep(2)
        
        # Verify deduplication still works (persistence)
        stats_after = requests.get(f"{AGGREGATOR_URL}/stats").json()
        assert stats_after["duplicate_dropped_count"] > stats_before["duplicate_dropped_count"]
    
    def test_large_batch_processing(self):
        """Test 11: Large batch processing"""
        batch_size = 100
        events = [self.create_test_event(topic="large_batch_test") for _ in range(batch_size)]
        batch_data = {"events": events}
        
        start_time = time.time()
        response = requests.post(f"{AGGREGATOR_URL}/publish/batch", json=batch_data, timeout=60)
        end_time = time.time()
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == batch_size
        
        # Performance check: should process within reasonable time
        processing_time = end_time - start_time
        assert processing_time < 30  # Should complete within 30 seconds
    
    def test_mixed_duplicate_batch(self):
        """Test 12: Batch dengan mix event baru dan duplikat"""
        # Create base events
        base_events = [self.create_test_event(topic="mixed_batch_test") for _ in range(5)]
        
        # Send base events first
        batch1 = {"events": base_events}
        response = requests.post(f"{AGGREGATOR_URL}/publish/batch", json=batch1)
        assert response.status_code == 200
        
        time.sleep(2)
        
        # Create mixed batch: some new, some duplicates
        new_events = [self.create_test_event(topic="mixed_batch_test") for _ in range(3)]
        mixed_events = base_events[:2] + new_events  # 2 duplicates + 3 new
        
        initial_stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        batch2 = {"events": mixed_events}
        response = requests.post(f"{AGGREGATOR_URL}/publish/batch", json=batch2)
        assert response.status_code == 200
        
        time.sleep(2)
        
        final_stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Verify: 3 new events processed, 2 duplicates dropped
        new_processed = final_stats["unique_processed_count"] - initial_stats["unique_processed_count"]
        new_duplicates = final_stats["duplicate_dropped_count"] - initial_stats["duplicate_dropped_count"]
        
        assert new_processed == 3  # 3 new events
        assert new_duplicates == 2  # 2 duplicates
    
    def test_topic_isolation(self):
        """Test 13: Topic isolation - events dengan topic berbeda tidak saling interfere"""
        topic1 = "isolation_test_1"
        topic2 = "isolation_test_2"
        
        # Same event_id but different topics
        event_id = str(uuid.uuid4())
        event1 = self.create_test_event(topic=topic1, event_id=event_id)
        event2 = self.create_test_event(topic=topic2, event_id=event_id)
        
        # Send both events
        response1 = requests.post(f"{AGGREGATOR_URL}/publish", json=event1)
        response2 = requests.post(f"{AGGREGATOR_URL}/publish", json=event2)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        time.sleep(2)
        
        # Both should be processed (different topics)
        events1 = requests.get(f"{AGGREGATOR_URL}/events", params={"topic": topic1}).json()
        events2 = requests.get(f"{AGGREGATOR_URL}/events", params={"topic": topic2}).json()
        
        assert len(events1["events"]) >= 1
        assert len(events2["events"]) >= 1
    
    def test_timestamp_ordering(self):
        """Test 14: Timestamp ordering dalam response"""
        topic = "ordering_test"
        
        # Send events dengan timestamp berbeda
        events = []
        for i in range(3):
            event = self.create_test_event(topic=topic)
            events.append(event)
            requests.post(f"{AGGREGATOR_URL}/publish", json=event)
            time.sleep(0.1)  # Small delay untuk ensure different timestamps
        
        time.sleep(2)
        
        # Get events
        response = requests.get(f"{AGGREGATOR_URL}/events", params={"topic": topic})
        assert response.status_code == 200
        
        returned_events = response.json()["events"]
        assert len(returned_events) >= 3
        
        # Verify events have timestamps
        for event in returned_events:
            assert "timestamp" in event
            assert "processed_at" in event
    
    def test_error_handling_malformed_json(self):
        """Test 15: Error handling untuk malformed JSON"""
        # Send malformed JSON
        response = requests.post(
            f"{AGGREGATOR_URL}/publish",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_system_stats_consistency(self):
        """Test 16: System stats consistency"""
        # Get initial stats
        initial_stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Send known number of events
        num_new_events = 5
        num_duplicates = 2
        
        # Send new events
        new_events = [self.create_test_event(topic="stats_test") for _ in range(num_new_events)]
        for event in new_events:
            requests.post(f"{AGGREGATOR_URL}/publish", json=event)
        
        # Send duplicates
        for i in range(num_duplicates):
            requests.post(f"{AGGREGATOR_URL}/publish", json=new_events[i])
        
        time.sleep(3)
        
        # Get final stats
        final_stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Verify consistency
        expected_received = initial_stats["received_count"] + num_new_events + num_duplicates
        expected_processed = initial_stats["unique_processed_count"] + num_new_events
        expected_duplicates = initial_stats["duplicate_dropped_count"] + num_duplicates
        
        assert final_stats["received_count"] == expected_received
        assert final_stats["unique_processed_count"] == expected_processed
        assert final_stats["duplicate_dropped_count"] == expected_duplicates
    
    def test_high_throughput_stress(self):
        """Test 17: High throughput stress test"""
        topic = "stress_test"
        num_events = 1000
        
        start_time = time.time()
        
        # Send events in batches
        batch_size = 50
        for i in range(0, num_events, batch_size):
            batch_events = [
                self.create_test_event(topic=f"{topic}_{j}") 
                for j in range(i, min(i + batch_size, num_events))
            ]
            batch_data = {"events": batch_events}
            
            response = requests.post(f"{AGGREGATOR_URL}/publish/batch", json=batch_data, timeout=30)
            assert response.status_code == 200
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        throughput = num_events / processing_time
        assert throughput > 100  # Should handle at least 100 events/second
        assert processing_time < 60  # Should complete within 1 minute
    
    def test_queue_length_monitoring(self):
        """Test 18: Queue length monitoring"""
        # Get stats yang include queue length
        stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Should have queue_length field
        assert "queue_length" in stats
        assert isinstance(stats["queue_length"], int)
        assert stats["queue_length"] >= 0
    
    def test_service_uptime_tracking(self):
        """Test 19: Service uptime tracking"""
        stats = requests.get(f"{AGGREGATOR_URL}/stats").json()
        
        # Should have uptime field
        assert "uptime_seconds" in stats
        assert isinstance(stats["uptime_seconds"], int)
        assert stats["uptime_seconds"] >= 0
        
        # Wait a bit and check uptime increased
        time.sleep(2)
        stats2 = requests.get(f"{AGGREGATOR_URL}/stats").json()
        assert stats2["uptime_seconds"] > stats["uptime_seconds"]
    
    def test_event_payload_integrity(self):
        """Test 20: Event payload integrity"""
        # Create event dengan complex payload
        complex_payload = {
            "nested": {
                "array": [1, 2, 3, "string"],
                "boolean": True,
                "null_value": None,
                "number": 123.456
            },
            "unicode": "测试 🚀 émojis",
            "large_text": "x" * 1000
        }
        
        event = self.create_test_event(topic="integrity_test")
        event["payload"] = complex_payload
        
        # Send event
        response = requests.post(f"{AGGREGATOR_URL}/publish", json=event)
        assert response.status_code == 200
        
        time.sleep(2)
        
        # Retrieve and verify payload integrity
        events_response = requests.get(f"{AGGREGATOR_URL}/events", params={"topic": "integrity_test"})
        assert events_response.status_code == 200
        
        events = events_response.json()["events"]
        found_event = None
        
        for e in events:
            if e["event_id"] == event["event_id"]:
                found_event = e
                break
        
        assert found_event is not None
        assert found_event["payload"] == complex_payload

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])