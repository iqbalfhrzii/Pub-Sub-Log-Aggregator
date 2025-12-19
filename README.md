# UAS Sistem Terdistribusi - Pub-Sub Log Aggregator

Sistem Pub-Sub log aggregator terdistribusi dengan idempotent consumer, deduplication, dan transaksi/kontrol konkurensi menggunakan Docker Compose.

## Arsitektur Sistem

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Publisher  │───▶│ Aggregator  │───▶│  Storage    │
│  Service    │    │  Service    │    │ (Postgres)  │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   Broker    │
                   │  (Redis)    │
                   └─────────────┘
```

### Komponen Sistem:

1. **Aggregator Service**: API utama untuk menerima dan memproses event
2. **Publisher Service**: Generator/simulator event dengan duplikasi
3. **Storage (PostgreSQL)**: Database persisten untuk deduplication dan penyimpanan event
4. **Broker (Redis)**: Message queue untuk async processing

## Fitur Utama

### 1. Idempotency & Deduplication
- Event dengan `(topic, event_id)` yang sama hanya diproses sekali
- Menggunakan unique constraint di database untuk atomicity
- Persistent deduplication store yang tahan restart container

### 2. Transaksi & Konkurensi
- Semua operasi database menggunakan transaksi ACID
- Isolation level: READ COMMITTED
- Upsert pattern dengan `INSERT ... ON CONFLICT DO NOTHING`
- Concurrent processing aman dari race conditions

### 3. Reliability
- At-least-once delivery dengan deduplication
- Crash tolerance dengan persistent storage
- Graceful error handling dan retry mechanisms

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (untuk development/testing)

### Menjalankan Sistem

1. **Build dan start semua services:**
```bash
docker compose up --build
```

2. **Akses aggregator API:**
```
http://localhost:8080
```

3. **Health check:**
```bash
curl http://localhost:8080/health
```

### Menjalankan Tests

1. **Install dependencies untuk testing:**
```bash
pip install pytest requests
```

2. **Pastikan sistem berjalan:**
```bash
docker compose up -d
```

3. **Run tests:**
```bash
cd tests
python -m pytest test_system.py -v
```

## API Endpoints

### POST /publish
Publish single event ke sistem.

**Request:**
```json
{
  "topic": "user_activity",
  "event_id": "unique-event-id",
  "timestamp": "2023-12-01T10:00:00Z",
  "source": "web_service",
  "payload": {
    "user_id": "123",
    "action": "login"
  }
}
```

**Response:**
```json
{
  "status": "accepted",
  "event_id": "unique-event-id",
  "topic": "user_activity",
  "message": "Event queued for processing"
}
```

### POST /publish/batch
Publish batch events dalam satu transaksi.

**Request:**
```json
{
  "events": [
    {
      "topic": "user_activity",
      "event_id": "event-1",
      "timestamp": "2023-12-01T10:00:00Z",
      "source": "web_service",
      "payload": {"action": "login"}
    },
    {
      "topic": "user_activity", 
      "event_id": "event-2",
      "timestamp": "2023-12-01T10:01:00Z",
      "source": "web_service",
      "payload": {"action": "logout"}
    }
  ]
}
```

### GET /events
Ambil daftar event yang telah diproses.

**Parameters:**
- `topic` (optional): Filter berdasarkan topic
- `limit` (optional): Jumlah maksimal event (default: 100, max: 1000)

**Response:**
```json
{
  "events": [
    {
      "topic": "user_activity",
      "event_id": "event-1",
      "timestamp": "2023-12-01T10:00:00Z",
      "source": "web_service",
      "payload": {"action": "login"},
      "processed_at": "2023-12-01T10:00:01Z"
    }
  ],
  "count": 1,
  "topic_filter": "user_activity",
  "limit": 100
}
```

### GET /stats
Ambil statistik sistem.

**Response:**
```json
{
  "received_count": 1000,
  "unique_processed_count": 700,
  "duplicate_dropped_count": 300,
  "topics_count": 5,
  "uptime_seconds": 3600,
  "queue_length": 0,
  "last_updated": "2023-12-01T10:00:00Z"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2023-12-01T10:00:00Z"
}
```

## Implementasi Teknis

### Database Schema

```sql
-- Tabel untuk menyimpan event yang telah diproses
CREATE TABLE processed_events (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(topic, event_id)  -- Constraint untuk deduplication
);

-- Tabel untuk statistik sistem
CREATE TABLE system_stats (
    id SERIAL PRIMARY KEY,
    received_count BIGINT DEFAULT 0,
    unique_processed_count BIGINT DEFAULT 0,
    duplicate_dropped_count BIGINT DEFAULT 0,
    topics_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW()
);
```

### Transaksi Pattern

```python
async def process_event_idempotent(self, event):
    async with conn.transaction(isolation='read_committed'):
        try:
            # Insert event baru
            await conn.execute("""
                INSERT INTO processed_events (topic, event_id, ...)
                VALUES ($1, $2, ...)
            """, ...)
            
            # Update statistik dalam transaksi yang sama
            await conn.execute("""
                UPDATE system_stats SET 
                    received_count = received_count + 1,
                    unique_processed_count = unique_processed_count + 1,
                    ...
            """)
            return True
            
        except UniqueViolationError:
            # Event duplikat, update hanya counter duplikat
            await conn.execute("""
                UPDATE system_stats SET 
                    received_count = received_count + 1,
                    duplicate_dropped_count = duplicate_dropped_count + 1,
                    ...
            """)
            return False
```

## Persistensi Data

Sistem menggunakan named volumes untuk persistensi:

- `postgres_data`: Data PostgreSQL
- `redis_data`: Data Redis
- `aggregator_logs`: Log aplikasi

Data akan tetap ada meskipun container dihapus dan dibuat ulang.

## Testing

Sistem dilengkapi dengan 20 comprehensive tests yang mencakup:

1. **Basic Functionality**: Health check, publish, get events
2. **Deduplication**: Single dan concurrent duplicate detection
3. **Batch Processing**: Batch publish dan mixed duplicate batches
4. **Concurrency**: Multi-threaded processing dan race condition prevention
5. **Persistence**: Data integrity setelah restart
6. **Performance**: High throughput dan stress testing
7. **Error Handling**: Invalid input dan malformed requests
8. **Stats Consistency**: Akurasi statistik sistem

### Menjalankan Specific Tests

```bash
# Test deduplication
python -m pytest test_system.py::TestPubSubAggregator::test_event_deduplication -v

# Test concurrency
python -m pytest test_system.py::TestPubSubAggregator::test_concurrent_duplicate_processing -v

# Test performance
python -m pytest test_system.py::TestPubSubAggregator::test_high_throughput_stress -v
```

## Monitoring & Observability

### Logs
- Structured logging dengan timestamp dan level
- Event processing logs dengan deduplication info
- Error logs dengan stack traces

### Metrics
- Real-time statistics via `/stats` endpoint
- Queue length monitoring
- Uptime tracking
- Throughput metrics

### Health Checks
- Database connectivity check
- Redis connectivity check
- Service readiness indicator

## Keamanan

- **Network Isolation**: Semua komunikasi dalam Docker network internal
- **No External Dependencies**: Tidak ada akses ke layanan eksternal
- **Non-root Containers**: Semua container berjalan sebagai non-root user
- **Input Validation**: Validasi ketat untuk semua input API

## Performance

Sistem didesain untuk menangani:
- **Throughput**: >100 events/second
- **Concurrent Processing**: Multiple workers tanpa race conditions
- **Large Batches**: Batch hingga 1000 events
- **High Duplicate Rate**: Efisien dengan 30%+ duplicate rate

## Troubleshooting

### Service tidak start
```bash
# Check logs
docker compose logs aggregator
docker compose logs storage

# Check health
curl http://localhost:8080/health
```

### Database connection issues
```bash
# Restart storage service
docker compose restart storage

# Check database logs
docker compose logs storage
```

### Performance issues
```bash
# Check queue length
curl http://localhost:8080/stats

# Monitor resource usage
docker stats
```

## Development

### Local Development Setup

1. **Setup Python environment:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r aggregator/requirements.txt
pip install pytest requests
```

2. **Start dependencies only:**
```bash
docker compose up storage broker -d
```

3. **Run aggregator locally:**
```bash
cd aggregator
DATABASE_URL=postgresql://user:pass@localhost:5432/aggregator_db \
REDIS_URL=redis://localhost:6379 \
python app.py
```

### Code Structure

```
aggregator/
├── app.py          # FastAPI application
├── database.py     # Database operations
├── Dockerfile      # Container definition
└── requirements.txt

publisher/
├── publisher.py    # Event generator
├── Dockerfile
└── requirements.txt

tests/
└── test_system.py  # Comprehensive test suite
```

## Video Demo

Link video demo: [YouTube Link akan ditambahkan]

Video demo mencakup:
- Arsitektur dan desain sistem
- Build dan deployment dengan Docker Compose
- Demonstrasi idempotency dan deduplication
- Concurrent processing dan transaksi
- Persistence setelah container restart
- Performance testing dan monitoring