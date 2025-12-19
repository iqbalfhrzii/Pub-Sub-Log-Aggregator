from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import logging
import os
import redis.asyncio as redis
from datetime import datetime, timezone
import json
import uuid

from database import Database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pub-Sub Log Aggregator", version="1.0.0")

# Models
class EventPayload(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    event_id: str = Field(..., min_length=1, max_length=255)
    timestamp: str = Field(..., description="ISO8601 timestamp")
    source: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any] = Field(...)

class BatchEvents(BaseModel):
    events: List[EventPayload]

# Global instances
db = Database()
redis_client: Optional[redis.Redis] = None
start_time = datetime.now(timezone.utc)

@app.on_event("startup")
async def startup_event():
    """Inisialisasi koneksi database dan Redis"""
    global redis_client
    
    await db.connect()
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    # Start background consumer
    asyncio.create_task(background_consumer())
    
    logger.info("Aggregator service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup saat shutdown"""
    await db.close()
    if redis_client:
        await redis_client.close()
    logger.info("Aggregator service shutdown")

async def background_consumer():
    """Background task untuk memproses event dari Redis queue"""
    while True:
        try:
            if redis_client:
                # Ambil event dari Redis queue dengan blocking pop
                result = await redis_client.blpop("event_queue", timeout=1)
                if result:
                    _, event_data = result
                    event = json.loads(event_data)
                    await db.process_event_idempotent(event)
        except Exception as e:
            logger.error(f"Background consumer error: {e}")
            await asyncio.sleep(1)

def validate_event(event: EventPayload) -> Dict[str, Any]:
    """Validasi dan normalisasi event"""
    try:
        # Validasi timestamp ISO8601
        datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        
        return {
            "topic": event.topic.strip(),
            "event_id": event.event_id.strip(),
            "timestamp": event.timestamp,
            "source": event.source.strip(),
            "payload": event.payload
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")

@app.post("/publish")
async def publish_event(event: EventPayload, background_tasks: BackgroundTasks):
    """
    Publish single event ke sistem
    Menggunakan Redis sebagai message broker untuk async processing
    """
    try:
        validated_event = validate_event(event)
        
        if redis_client:
            # Push ke Redis queue untuk async processing
            await redis_client.rpush("event_queue", json.dumps(validated_event))
            logger.info(f"Event queued: {validated_event['topic']}/{validated_event['event_id']}")
        else:
            # Fallback: process directly jika Redis tidak tersedia
            await db.process_event_idempotent(validated_event)
        
        return {
            "status": "accepted",
            "event_id": validated_event["event_id"],
            "topic": validated_event["topic"],
            "message": "Event queued for processing"
        }
    
    except Exception as e:
        logger.error(f"Publish error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish/batch")
async def publish_batch(batch: BatchEvents):
    """
    Publish batch events dengan transaksi atomik
    Semua event berhasil atau semua gagal
    """
    try:
        validated_events = []
        for event in batch.events:
            validated_events.append(validate_event(event))
        
        if redis_client:
            # Push semua event ke queue dalam satu operasi
            pipe = redis_client.pipeline()
            for event in validated_events:
                pipe.rpush("event_queue", json.dumps(event))
            await pipe.execute()
            
            logger.info(f"Batch of {len(validated_events)} events queued")
        else:
            # Fallback: process semua event secara langsung
            for event in validated_events:
                await db.process_event_idempotent(event)
        
        return {
            "status": "accepted",
            "count": len(validated_events),
            "message": f"Batch of {len(validated_events)} events queued for processing"
        }
    
    except Exception as e:
        logger.error(f"Batch publish error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events")
async def get_events(topic: Optional[str] = None, limit: int = 100):
    """Ambil daftar event yang telah diproses"""
    try:
        if limit > 1000:
            limit = 1000  # Batasi untuk performa
        
        events = await db.get_events(topic, limit)
        
        # Convert datetime objects to ISO string
        for event in events:
            if 'timestamp' in event and isinstance(event['timestamp'], datetime):
                event['timestamp'] = event['timestamp'].isoformat()
            if 'processed_at' in event and isinstance(event['processed_at'], datetime):
                event['processed_at'] = event['processed_at'].isoformat()
        
        return {
            "events": events,
            "count": len(events),
            "topic_filter": topic,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"Get events error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Ambil statistik sistem"""
    try:
        stats = await db.get_stats()
        
        # Convert datetime to ISO string
        if 'last_updated' in stats and isinstance(stats['last_updated'], datetime):
            stats['last_updated'] = stats['last_updated'].isoformat()
        
        # Tambah uptime
        uptime_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
        stats['uptime_seconds'] = int(uptime_seconds)
        
        # Tambah queue info jika Redis tersedia
        if redis_client:
            try:
                queue_length = await redis_client.llen("event_queue")
                stats['queue_length'] = queue_length
            except:
                stats['queue_length'] = 0
        else:
            stats['queue_length'] = 0
        
        return stats
    
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await db.get_stats()
        
        # Test Redis connection
        redis_status = "connected"
        if redis_client:
            try:
                await redis_client.ping()
            except:
                redis_status = "disconnected"
        else:
            redis_status = "not_configured"
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": redis_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)