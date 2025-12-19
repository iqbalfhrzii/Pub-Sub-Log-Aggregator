# DEMO COMMANDS - UAS Sistem Terdistribusi

## PRE-RECORDING SETUP

```powershell
docker compose down
docker system prune -f
python check_db.py
python test_exact_url.py
docker compose up broker -d
python simple_run.py
```

## TEST KONEKSI

```powershell
curl http://localhost:8081/health | ConvertFrom-Json | ConvertTo-Json -Depth 10
curl http://localhost:8081/stats | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

## POIN 1 - ARSITEKTUR

```powershell
tree /F
code docker-compose.yml
code aggregator/database.py
```

## POIN 2 - BUILD & COMPOSE

```powershell
docker compose up --build -d
docker compose ps
```

## POIN 3 - IDEMPOTENCY & DUPLICATE DETECTION

### Stats SEBELUM
```powershell
curl http://localhost:8081/stats | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Event PERTAMA
```powershell
curl -X POST http://localhost:8081/publish -H 'Content-Type: application/json' -d '{"topic":"demo","event_id":"test-001","timestamp":"2023-12-19T10:00:00Z","source":"test","payload":{"test":true}}' | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Event DUPLIKAT (sama persis)
```powershell
curl -X POST http://localhost:8081/publish -H 'Content-Type: application/json' -d '{"topic":"demo","event_id":"test-001","timestamp":"2023-12-19T10:00:00Z","source":"test","payload":{"test":true}}' | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Stats SESUDAH
```powershell
curl http://localhost:8081/stats | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

## POIN 4 - TRANSAKSI & KONKURENSI

```powershell
python comprehensive_test.py
python debug_duplicate.py
code aggregator/database.py
```

## POIN 5 - GET ENDPOINTS

```powershell
curl http://localhost:8081/events?limit=3 | ConvertFrom-Json | ConvertTo-Json -Depth 10
curl 'http://localhost:8081/events?topic=demo&limit=2' | ConvertFrom-Json | ConvertTo-Json -Depth 10
curl http://localhost:8081/stats | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

## POIN 6 - PERSISTENCE

### Stats sebelum restart
```powershell
curl http://localhost:8081/stats | ConvertFrom-Json | ConvertTo-Json -Depth 10
curl http://localhost:8081/events?limit=2 | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Stop aggregator (Ctrl+C di terminal)
### Restart database
```powershell
docker compose restart storage
```

### Start aggregator lagi
```powershell
python simple_run.py
```

### Stats setelah restart (data masih ada)
```powershell
curl http://localhost:8081/stats | ConvertFrom-Json | ConvertTo-Json -Depth 10
curl http://localhost:8081/events?limit=2 | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Show volumes
```powershell
docker volume ls
docker volume inspect uas_postgres_data
```

## POIN 7 - NETWORK SECURITY

```powershell
docker network ls
docker network inspect uas_uas_network
code aggregator/Dockerfile
```

## POIN 8 - OBSERVABILITY

```powershell
python final_demo.py
docker compose logs storage --tail=10
python -m pytest tests/test_system.py::TestPubSubAggregator::test_event_deduplication -v
```

## BATCH EVENT EXAMPLE (jika diperlukan)

```powershell
curl -X POST http://localhost:8081/publish/batch -H 'Content-Type: application/json' -d '{"events":[{"topic":"batch_test","event_id":"batch-001","timestamp":"2023-12-19T10:01:00Z","source":"batch_source","payload":{"batch":true}},{"topic":"batch_test","event_id":"batch-002","timestamp":"2023-12-19T10:02:00Z","source":"batch_source","payload":{"batch":true}}]}' | ConvertFrom-Json | ConvertTo-Json -Depth 10
```