import requests
import json
import time
import random
import os
import logging
from datetime import datetime, timezone
from faker import Faker
from typing import List, Dict, Any
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

fake = Faker()

class EventPublisher:
    def __init__(self, aggregator_url: str):
        self.aggregator_url = aggregator_url.rstrip('/')
        self.session = requests.Session()
        self.published_events = []  # Track untuk duplikasi
        
    def generate_event(self, topic: str = None, duplicate_existing: bool = False) -> Dict[str, Any]:
        """Generate event, dengan opsi untuk membuat duplikat"""
        
        if duplicate_existing and self.published_events:
            # Pilih event yang sudah ada untuk diduplikasi
            existing_event = random.choice(self.published_events)
            logger.info(f"Creating duplicate of event: {existing_event['event_id']}")
            return existing_event.copy()
        
        # Generate event baru
        if not topic:
            topic = random.choice(['user_activity', 'system_logs', 'transactions', 'notifications', 'errors'])
        
        event = {
            "topic": topic,
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": f"service_{random.randint(1, 5)}",
            "payload": {
                "user_id": fake.uuid4(),
                "action": fake.word(),
                "details": fake.text(max_nb_chars=100),
                "metadata": {
                    "ip_address": fake.ipv4(),
                    "user_agent": fake.user_agent(),
                    "session_id": fake.uuid4()
                }
            }
        }
        
        # Simpan untuk kemungkinan duplikasi
        self.published_events.append(event)
        return event
    
    def publish_single_event(self, event: Dict[str, Any]) -> bool:
        """Publish single event ke aggregator"""
        try:
            response = self.session.post(
                f"{self.aggregator_url}/publish",
                json=event,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Event published successfully: {event['event_id']}")
                return True
            else:
                logger.error(f"Failed to publish event: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return False
    
    def publish_batch_events(self, events: List[Dict[str, Any]]) -> bool:
        """Publish batch events ke aggregator"""
        try:
            batch_data = {"events": events}
            response = self.session.post(
                f"{self.aggregator_url}/publish/batch",
                json=batch_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Batch of {len(events)} events published successfully")
                return True
            else:
                logger.error(f"Failed to publish batch: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Batch request failed: {e}")
            return False
    
    def run_simulation(self, total_events: int = 20000, duplicate_rate: float = 0.3, batch_size: int = 10):
        """
        Jalankan simulasi pengiriman event dengan duplikasi
        
        Args:
            total_events: Total event yang akan dikirim
            duplicate_rate: Persentase event duplikat (0.0 - 1.0)
            batch_size: Ukuran batch untuk batch publishing
        """
        logger.info(f"Starting simulation: {total_events} events, {duplicate_rate*100}% duplicates")
        
        published_count = 0
        duplicate_count = 0
        batch_count = 0
        
        start_time = time.time()
        
        while published_count < total_events:
            # Tentukan apakah akan membuat duplikat
            should_duplicate = (
                random.random() < duplicate_rate and 
                len(self.published_events) > 0 and
                duplicate_count < total_events * duplicate_rate
            )
            
            # Generate batch events
            batch_events = []
            for _ in range(min(batch_size, total_events - published_count)):
                event = self.generate_event(duplicate_existing=should_duplicate)
                batch_events.append(event)
                
                if should_duplicate:
                    duplicate_count += 1
                
                published_count += 1
            
            # Publish batch
            if self.publish_batch_events(batch_events):
                batch_count += 1
            
            # Progress logging
            if published_count % 1000 == 0:
                elapsed = time.time() - start_time
                rate = published_count / elapsed if elapsed > 0 else 0
                logger.info(f"Progress: {published_count}/{total_events} events, "
                           f"{duplicate_count} duplicates, {rate:.1f} events/sec")
            
            # Small delay untuk tidak overwhelm sistem
            time.sleep(0.01)
        
        # Final statistics
        elapsed = time.time() - start_time
        total_rate = published_count / elapsed if elapsed > 0 else 0
        
        logger.info(f"Simulation completed!")
        logger.info(f"Total events: {published_count}")
        logger.info(f"Duplicate events: {duplicate_count} ({duplicate_count/published_count*100:.1f}%)")
        logger.info(f"Batches sent: {batch_count}")
        logger.info(f"Total time: {elapsed:.2f} seconds")
        logger.info(f"Average rate: {total_rate:.1f} events/sec")
        
        return {
            'total_events': published_count,
            'duplicate_events': duplicate_count,
            'batches_sent': batch_count,
            'elapsed_time': elapsed,
            'events_per_second': total_rate
        }

def wait_for_aggregator(url: str, max_retries: int = 30):
    """Wait untuk aggregator service siap"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("Aggregator service is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        
        logger.info(f"Waiting for aggregator service... ({i+1}/{max_retries})")
        time.sleep(2)
    
    logger.error("Aggregator service not available")
    return False

def main():
    aggregator_url = os.getenv("AGGREGATOR_URL", "http://localhost:8080")
    
    logger.info(f"Publisher starting, target: {aggregator_url}")
    
    # Wait untuk aggregator service
    if not wait_for_aggregator(aggregator_url):
        return
    
    # Buat publisher instance
    publisher = EventPublisher(aggregator_url)
    
    # Jalankan simulasi
    try:
        # Simulasi dengan 20k events, 30% duplikat
        results = publisher.run_simulation(
            total_events=20000,
            duplicate_rate=0.3,
            batch_size=20
        )
        
        # Tunggu sebentar lalu cek statistik
        time.sleep(5)
        
        try:
            stats_response = requests.get(f"{aggregator_url}/stats", timeout=10)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                logger.info("Final aggregator statistics:")
                logger.info(f"  Received: {stats.get('received_count', 0)}")
                logger.info(f"  Unique processed: {stats.get('unique_processed_count', 0)}")
                logger.info(f"  Duplicates dropped: {stats.get('duplicate_dropped_count', 0)}")
                logger.info(f"  Topics: {stats.get('topics_count', 0)}")
        except Exception as e:
            logger.error(f"Failed to get final stats: {e}")
        
    except KeyboardInterrupt:
        logger.info("Publisher stopped by user")
    except Exception as e:
        logger.error(f"Publisher error: {e}")

if __name__ == "__main__":
    main()