import asyncpg
import asyncio
import os
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/aggregator_db")
    
    async def connect(self):
        """Inisialisasi koneksi database dan buat tabel"""
        try:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=5, max_size=20)
            await self.create_tables()
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def create_tables(self):
        """Buat tabel dengan constraint unik untuk deduplication"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    event_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    source VARCHAR(255) NOT NULL,
                    payload JSONB NOT NULL,
                    processed_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(topic, event_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_topic_timestamp ON processed_events(topic, timestamp);
                CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_events(processed_at);
                
                CREATE TABLE IF NOT EXISTS system_stats (
                    id SERIAL PRIMARY KEY,
                    received_count BIGINT DEFAULT 0,
                    unique_processed_count BIGINT DEFAULT 0,
                    duplicate_dropped_count BIGINT DEFAULT 0,
                    topics_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT NOW()
                );
                
                INSERT INTO system_stats (received_count, unique_processed_count, duplicate_dropped_count, topics_count)
                SELECT 0, 0, 0, 0
                WHERE NOT EXISTS (SELECT 1 FROM system_stats);
            """)
    
    async def process_event_idempotent(self, event: Dict[str, Any]) -> bool:
        """
        Proses event dengan idempotency menggunakan transaksi ACID
        Returns True jika event baru diproses, False jika duplikat
        """
        async with self.pool.acquire() as conn:
            try:
                # Parse timestamp dengan timezone handling
                timestamp_str = event['timestamp']
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str[:-1] + '+00:00'
                
                parsed_timestamp = datetime.fromisoformat(timestamp_str)
                # Convert to UTC if timezone aware
                if parsed_timestamp.tzinfo is not None:
                    parsed_timestamp = parsed_timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                
                # Try insert dalam transaksi terpisah
                async with conn.transaction(isolation='read_committed'):
                    await conn.execute("""
                        INSERT INTO processed_events (topic, event_id, timestamp, source, payload)
                        VALUES ($1, $2, $3, $4, $5)
                    """, event['topic'], event['event_id'], parsed_timestamp,
                        event['source'], json.dumps(event['payload']))
                    
                    # Update statistik untuk event baru
                    await conn.execute("""
                        UPDATE system_stats SET 
                            received_count = received_count + 1,
                            unique_processed_count = unique_processed_count + 1,
                            topics_count = (SELECT COUNT(DISTINCT topic) FROM processed_events),
                            last_updated = NOW()
                    """)
                
                logger.info(f"New event processed: {event['topic']}/{event['event_id']}")
                return True
                
            except asyncpg.UniqueViolationError:
                # Event duplikat, update counter dalam transaksi terpisah
                async with conn.transaction(isolation='read_committed'):
                    await conn.execute("""
                        UPDATE system_stats SET 
                            received_count = received_count + 1,
                            duplicate_dropped_count = duplicate_dropped_count + 1,
                            last_updated = NOW()
                    """)
                
                logger.info(f"Duplicate event dropped: {event['topic']}/{event['event_id']}")
                return False
    
    async def get_events(self, topic: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Ambil daftar event yang telah diproses"""
        async with self.pool.acquire() as conn:
            if topic:
                rows = await conn.fetch("""
                    SELECT topic, event_id, timestamp, source, payload, processed_at
                    FROM processed_events 
                    WHERE topic = $1 
                    ORDER BY processed_at DESC 
                    LIMIT $2
                """, topic, limit)
            else:
                rows = await conn.fetch("""
                    SELECT topic, event_id, timestamp, source, payload, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC 
                    LIMIT $1
                """, limit)
            
            result = []
            for row in rows:
                row_dict = dict(row)
                # Parse JSON payload back to dict
                if 'payload' in row_dict and isinstance(row_dict['payload'], str):
                    try:
                        row_dict['payload'] = json.loads(row_dict['payload'])
                    except:
                        pass  # Keep as string if parsing fails
                result.append(row_dict)
            return result
    
    async def get_stats(self) -> Dict[str, Any]:
        """Ambil statistik sistem"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM system_stats ORDER BY id DESC LIMIT 1")
            if row:
                return dict(row)
            return {
                'received_count': 0,
                'unique_processed_count': 0,
                'duplicate_dropped_count': 0,
                'topics_count': 0,
                'last_updated': datetime.now()
            }
    
    async def close(self):
        """Tutup koneksi database"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")