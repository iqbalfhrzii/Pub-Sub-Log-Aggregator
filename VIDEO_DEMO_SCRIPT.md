# Video Demo Script - UAS Sistem Terdistribusi
## Pub-Sub Log Aggregator dengan Idempotency & Transaksi

**Durasi Target: 20-25 menit**

## 🎯 **CHECKLIST POIN WAJIB RUBRIK**

**Semua poin ini WAJIB ditampilkan dalam video:**
- ✅ **Poin 1**: Arsitektur multi-service dan alasan desain
- ✅ **Poin 2**: Proses build image dan menjalankan Compose
- ✅ **Poin 3**: Pengiriman event duplikat dan bukti idempotency + dedup
- ✅ **Poin 4**: Demonstrasi transaksi/konkurensi (multi-worker) dan hasil konsisten
- ✅ **Poin 5**: GET /events dan GET /stats sebelum/sesudah
- ✅ **Poin 6**: Crash/recreate container + bukti data persisten via volumes
- ✅ **Poin 7**: Keamanan jaringan lokal (tidak ada dependensi eksternal)
- ✅ **Poin 8**: Observability (logging, metrik), serta ringkasan keputusan desain

---

## 🎬 **BAGIAN 1: ARSITEKTUR MULTI-SERVICE & ALASAN DESAIN (3-4 menit)**
**📋 RUBRIK POIN 1: Arsitektur multi-service dan alasan desain**

### **Slide 1: Judul & Identitas**
```
- Nama: [Nama Anda]
- NIM: [NIM Anda]
- Mata Kuliah: Sistem Terdistribusi
- Tema: Pub-Sub Log Aggregator dengan Idempotent Consumer
```

### **Slide 2: Arsitektur Sistem**
**Tampilkan diagram:**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Publisher  │───▶│ Aggregator  │───▶│ PostgreSQL  │
│  Service    │    │  Service    │    │  Database   │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    Redis    │
                   │   Broker    │
                   └─────────────┘
```

**Narasi:**
> "Sistem ini terdiri dari 4 komponen utama yang berjalan dalam Docker Compose:
> 1. Aggregator Service - API utama dengan FastAPI
> 2. Publisher Service - Generator event dengan duplikasi
> 3. PostgreSQL - Database persisten untuk deduplication
> 4. Redis - Message broker untuk async processing"

### **Slide 3: Fitur Utama**
**Tampilkan:**
- ✅ Idempotent Consumer
- ✅ Strong Deduplication  
- ✅ ACID Transactions
- ✅ Concurrent Processing Safety
- ✅ Persistent Storage
- ✅ Docker Compose Orchestration

---

## 🛠️ **BAGIAN 2: BUILD IMAGE & DOCKER COMPOSE (4-5 menit)**
**📋 RUBRIK POIN 2: Proses build image dan menjalankan Compose**

### **Demo 1: Project Structure**
**Buka terminal dan tampilkan:**
```bash
cd "C:\Users\HP VICTUS\Documents\Docker Tutorial\UAS"
tree /F
```

**Narasi:**
> "Mari kita lihat struktur project. Kita punya direktori aggregator dengan FastAPI, publisher untuk generate events, tests untuk testing, dan docker-compose.yml untuk orchestration."

### **Demo 2: Docker Compose Configuration**
**Buka file `docker-compose.yml`:**
```bash
code docker-compose.yml
```

**Highlight:**
- Service definitions
- Named volumes untuk persistensi
- Internal network isolation
- Environment variables

### **Demo 3: Database Schema**
**Buka `aggregator/database.py`:**
```bash
code aggregator/database.py
```

**Highlight:**
- Unique constraint `(topic, event_id)`
- ACID transaction implementation
- Error handling untuk duplicate detection

### **Demo 4: Build & Start System**
```bash
# Stop any running containers
docker compose down

# Build and start all services (WAJIB DITAMPILKAN)
docker compose up --build -d

# Check status
docker compose ps

# Start aggregator locally (karena kita pakai PostgreSQL lokal)
python simple_run.py
```

**Narasi:**
> "Sekarang kita build dan start semua services. Docker Compose akan membuat network internal, volumes untuk persistensi, dan menjalankan semua containers."

---

## 🔧 **BAGIAN 3: IDEMPOTENCY & DUPLICATE DETECTION (6-7 menit)**
**📋 RUBRIK POIN 3: Pengiriman event duplikat dan bukti idempotency + dedup**
**📋 RUBRIK POIN 5: GET /events dan GET /stats sebelum/sesudah**

### **Demo 5: Health Check**
```bash
curl http://localhost:8081/health
```

**Tampilkan response JSON dan jelaskan status database & redis connection.**

### **Demo 6: Initial Statistics (SEBELUM)**
```bash
curl http://localhost:8081/stats
```

**Narasi:**
> "Ini adalah statistik awal sistem. Semua counter masih 0 karena belum ada event yang diproses."

### **Demo 7: Single Event Publishing (EVENT PERTAMA)**
```bash
curl -X POST http://localhost:8081/publish \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "demo_topic",
    "event_id": "demo-001",
    "timestamp": "2023-12-19T10:00:00Z",
    "source": "demo_source",
    "payload": {"message": "first event", "test": true}
  }'
```

**Tampilkan response dan jelaskan `processed: true`.**

### **Demo 8: Duplicate Detection (EVENT DUPLIKAT - WAJIB)**
**Kirim event yang PERSIS SAMA:**
```bash
curl -X POST http://localhost:8081/publish \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "demo_topic",
    "event_id": "demo-001",
    "timestamp": "2023-12-19T10:00:00Z",
    "source": "demo_source",
    "payload": {"message": "first event", "test": true}
  }'
```

**Tampilkan response `processed: false` dan jelaskan duplicate detection.**

### **Demo 9: Batch Publishing**
```bash
curl -X POST http://localhost:8080/publish/batch \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "topic": "transactions",
        "event_id": "txn-001",
        "timestamp": "2023-12-19T10:01:00Z",
        "source": "payment_service",
        "payload": {"amount": 100, "currency": "USD"}
      },
      {
        "topic": "transactions", 
        "event_id": "txn-002",
        "timestamp": "2023-12-19T10:02:00Z",
        "source": "payment_service",
        "payload": {"amount": 200, "currency": "USD"}
      }
    ]
  }'
```

### **Demo 10: Data Retrieval & Stats (SESUDAH)**
```bash
# Get all events
curl http://localhost:8081/events

# Get events by topic
curl "http://localhost:8081/events?topic=demo_topic"

# Check updated stats (WAJIB BANDINGKAN DENGAN SEBELUM)
curl http://localhost:8081/stats
```

---

## ⚡ **BAGIAN 4: TRANSAKSI & KONKURENSI MULTI-WORKER (5-6 menit)**
**📋 RUBRIK POIN 4: Demonstrasi transaksi/konkurensi (multi-worker) dan hasil konsisten**

### **Demo 11: Concurrent Processing Test**
**Jalankan script test:**
```bash
python comprehensive_test.py
```

**Narasi:**
> "Script ini mengirim multiple events secara concurrent untuk membuktikan sistem aman dari race conditions. Kita menggunakan ThreadPoolExecutor untuk simulasi concurrent access."

### **Demo 12: Database Transaction Inspection**
**Buka database dan tampilkan:**
```bash
# Connect to PostgreSQL
docker exec -it uas-storage-1 psql -U postgres -d aggregator_db

# Show processed events
SELECT topic, event_id, processed_at FROM processed_events ORDER BY processed_at DESC LIMIT 10;

# Show statistics
SELECT * FROM system_stats;

# Exit
\q
```

### **Demo 13: Isolation Level Explanation**
**Buka `database.py` dan highlight:**
- `isolation='read_committed'`
- Transaction boundaries
- UniqueViolationError handling

**Narasi:**
> "Kita menggunakan READ COMMITTED isolation level yang memberikan balance antara consistency dan performance. Setiap event processing dilakukan dalam transaksi terpisah untuk menghindari deadlock."

---

## 🔄 **BAGIAN 5: CRASH/RECREATE & DATA PERSISTEN (4-5 menit)**
**📋 RUBRIK POIN 6: Crash/recreate container + bukti data persisten via volumes**

### **Demo 14: Data Persistence Test (WAJIB)**
**Tampilkan current stats SEBELUM restart:**
```bash
curl http://localhost:8081/stats
curl http://localhost:8081/events
```

**Stop aggregator dan database containers:**
```bash
# Stop aggregator (Ctrl+C di terminal)
# Stop database container
docker compose stop storage
docker compose start storage
```

**Restart aggregator dan check data MASIH ADA:**
```bash
python simple_run.py
# Di terminal baru:
curl http://localhost:8081/stats
curl http://localhost:8081/events
```

**Narasi:**
> "Setelah container restart, data tetap ada karena menggunakan named volumes. Ini membuktikan persistensi data yang aman."

### **Demo 15: Volume Inspection**
```bash
# Show volumes
docker volume ls

# Inspect postgres volume
docker volume inspect uas_postgres_data
```

---

## 🧪 **BAGIAN 6: OBSERVABILITY & LOGGING (3-4 menit)**
**📋 RUBRIK POIN 8: Observability (logging, metrik), serta ringkasan keputusan desain**

### **Demo 16: Comprehensive Testing**
```bash
# Run specific tests
python -m pytest tests/test_system.py::TestPubSubAggregator::test_event_deduplication -v

python -m pytest tests/test_system.py::TestPubSubAggregator::test_concurrent_duplicate_processing -v
```

### **Demo 17: Logging & Monitoring (WAJIB)**
**Tampilkan logs aggregator:**
```bash
# Lihat logs dari terminal yang menjalankan aggregator
# Atau check logs database
docker compose logs storage --tail=10
```

**Highlight structured logging dengan:**
- Timestamp
- Log levels
- Event processing info
- Duplicate detection logs

### **Demo 18: Performance Metrics**
```bash
# Run performance test
python final_demo.py
```

**Tampilkan hasil throughput dan deduplication rate.**

---

## 🔒 **BAGIAN 7: KEAMANAN JARINGAN LOKAL (2-3 menit)**
**📋 RUBRIK POIN 7: Keamanan jaringan lokal (tidak ada dependensi eksternal)**

### **Demo 19: Network Security**
```bash
# Show Docker networks
docker network ls

# Inspect internal network
docker network inspect uas_uas_network
```

**Narasi:**
> "Semua services berjalan dalam internal Docker network. Tidak ada akses ke layanan eksternal, memastikan keamanan dan isolasi."

### **Demo 20: Container Security**
**Tampilkan Dockerfile:**
```bash
code aggregator/Dockerfile
```

**Highlight:**
- Non-root user
- Minimal base image
- Security best practices

---

## 📊 **BAGIAN 8: RINGKASAN KEPUTUSAN DESAIN & HASIL (2-3 menit)**
**📋 RUBRIK POIN 8: Ringkasan keputusan desain**

### **Slide 4: Achievement Summary**
**Tampilkan:**
- ✅ Perfect Idempotency (100% duplicate detection)
- ✅ ACID Transactions (READ COMMITTED isolation)
- ✅ Crash Tolerance (persistent volumes)
- ✅ High Performance (>100 events/second)
- ✅ 20 Comprehensive Tests
- ✅ Production Ready Architecture

### **Demo 21: Final Statistics**
```bash
curl http://localhost:8081/stats
```

**Narasi hasil akhir:**
> "Dalam demo ini kita berhasil memproses [X] events dengan [Y] duplicates detected. Deduplication rate mencapai [Z]% dengan zero errors."

### **Slide 5: Technical Highlights**
- **Database**: PostgreSQL dengan unique constraints
- **Transactions**: ACID compliance dengan proper isolation
- **Concurrency**: Race condition free dengan atomic operations  
- **Persistence**: Named volumes untuk data safety
- **Testing**: 20 test cases covering all scenarios
- **Documentation**: Comprehensive README dan report

### **Slide 6: Repository & Submission**
```
GitHub Repository: [Your GitHub Link]
├── aggregator/     # FastAPI service
├── publisher/      # Event generator  
├── tests/         # 20 test cases
├── docker-compose.yml
├── README.md      # Complete documentation
└── report.md      # Theoretical analysis
```

---

## 🚀 **QUICK SETUP SEBELUM RECORDING**

```bash
# 1. Pastikan sistem bersih
docker compose down
docker system prune -f

# 2. Setup database
python check_db.py
python test_exact_url.py

# 3. Start Redis
docker compose up broker -d

# 4. Start aggregator
python simple_run.py
# (biarkan running di background)
```

## 🎬 **COMMAND CHEAT SHEET UNTUK DEMO**

**Poin 1 - Arsitektur:**
```bash
tree /F
code docker-compose.yml
code aggregator/database.py
```

**Poin 2 - Build & Compose:**
```bash
docker compose up --build -d
docker compose ps
python simple_run.py
```

**Poin 3 - Idempotency:**
```bash
# Stats awal
curl http://localhost:8081/stats

# Event pertama
curl -X POST http://localhost:8081/publish -H "Content-Type: application/json" -d '{"topic":"demo","event_id":"test-001","timestamp":"2023-12-19T10:00:00Z","source":"test","payload":{"test":true}}'

# Event duplikat (sama persis)
curl -X POST http://localhost:8081/publish -H "Content-Type: application/json" -d '{"topic":"demo","event_id":"test-001","timestamp":"2023-12-19T10:00:00Z","source":"test","payload":{"test":true}}'

# Stats akhir
curl http://localhost:8081/stats
```

**Poin 4 - Konkurensi:**
```bash
python comprehensive_test.py
python debug_duplicate.py
```

**Poin 5 - GET endpoints:**
```bash
curl http://localhost:8081/events
curl http://localhost:8081/stats
```

**Poin 6 - Persistence:**
```bash
# Sebelum restart
curl http://localhost:8081/stats

# Restart (Ctrl+C aggregator, lalu start lagi)
python simple_run.py

# Setelah restart
curl http://localhost:8081/stats
```

**Poin 7 - Network Security:**
```bash
docker network ls
docker network inspect uas_uas_network
```

**Poin 8 - Observability:**
```bash
python final_demo.py
docker compose logs storage --tail=10
```    # Theoretical analysis
```

---

## 🎯 **CHECKLIST DEMO REQUIREMENTS**

**Wajib ditampilkan dalam video:**
- [x] Arsitektur multi-service dan alasan desain
- [x] Proses build image dan menjalankan Compose
- [x] Pengiriman event duplikat dan bukti idempotency
- [x] Demonstrasi transaksi/konkurensi dan hasil konsisten
- [x] GET /events dan GET /stats sebelum/sesudah
- [x] Crash/recreate container + bukti data persisten
- [x] Keamanan jaringan lokal (tidak ada dependensi eksternal)
- [x] Observability (logging, metrik)
- [x] Ringkasan keputusan desain

---

## 📝 **TIPS RECORDING**

1. **Persiapan:**
   - Clean desktop
   - Close unnecessary applications
   - Test audio/video quality
   - Prepare slides in advance

2. **During Recording:**
   - Speak clearly dan tidak terlalu cepat
   - Explain setiap step yang dilakukan
   - Show results clearly
   - Highlight key technical points

3. **Technical Setup:**
   - Use high resolution (1080p minimum)
   - Ensure terminal text is readable
   - Use zoom when showing code
   - Keep consistent audio level

4. **Content Flow:**
   - Follow script structure
   - Don't skip required demo points
   - Explain technical decisions
   - Show actual working system

**Target Duration: 20-25 menit maksimal**