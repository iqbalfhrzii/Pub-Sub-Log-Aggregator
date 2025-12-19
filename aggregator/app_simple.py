from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timezone
import json

from database import Database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db = Database()
start_time = datetime.now(timezone.utc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    logger.info("Aggregator service started successfully")
    yield
    # Shutdown
    await db.close()
    logger.info("Aggregator service shutdown")

app = FastAPI(title="Pub-Sub Log Aggregator", version="1.0.0", lifespan=lifespan)

# Models
class EventPayload(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    event_id: str = Field(..., min_length=1, max_length=255)
    timestamp: str = Field(..., description="ISO8601 timestamp")
    source: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any] = Field(...)

class BatchEvents(BaseModel):
    events: List[EventPayload]

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
async def publish_event(event: EventPayload):
    """
    Publish single event ke sistem
    Langsung proses tanpa queue untuk simplicity
    """
    try:
        validated_event = validate_event(event)
        
        # Process directly
        processed = await db.process_event_idempotent(validated_event)
        
        if processed:
            logger.info(f"Event processed: {validated_event['topic']}/{validated_event['event_id']}")
            message = "Event processed successfully"
        else:
            logger.info(f"Duplicate event dropped: {validated_event['topic']}/{validated_event['event_id']}")
            message = "Duplicate event dropped"
        
        return {
            "status": "accepted",
            "event_id": validated_event["event_id"],
            "topic": validated_event["topic"],
            "message": message,
            "processed": processed
        }
    
    except Exception as e:
        logger.error(f"Publish error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish/batch")
async def publish_batch(batch: BatchEvents):
    """
    Publish batch events dengan transaksi atomik
    """
    try:
        validated_events = []
        for event in batch.events:
            validated_events.append(validate_event(event))
        
        processed_count = 0
        duplicate_count = 0
        
        # Process each event
        for event in validated_events:
            processed = await db.process_event_idempotent(event)
            if processed:
                processed_count += 1
            else:
                duplicate_count += 1
        
        logger.info(f"Batch processed: {processed_count} new, {duplicate_count} duplicates")
        
        return {
            "status": "accepted",
            "count": len(validated_events),
            "processed": processed_count,
            "duplicates": duplicate_count,
            "message": f"Batch processed: {processed_count} new events, {duplicate_count} duplicates"
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
        
        # No queue in simple version
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
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "not_used",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)