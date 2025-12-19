import asyncpg
import asyncio

async def test_connection():
    try:
        # Test koneksi dengan kredensial yang berbeda
        conn = await asyncpg.connect("postgresql://postgres:admin@localhost:5432/aggregator_db")
        print("[OK] Koneksi berhasil dengan postgres:admin")
        
        # Buat tabel
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
        """)
        print("[OK] Tabel berhasil dibuat")
        
        # Insert initial stats
        await conn.execute("""
            INSERT INTO system_stats (received_count, unique_processed_count, duplicate_dropped_count, topics_count)
            SELECT 0, 0, 0, 0
            WHERE NOT EXISTS (SELECT 1 FROM system_stats);
        """)
        print("[OK] Data awal berhasil diinsert")
        
        await conn.close()
        print("[OK] Setup database selesai!")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        
        # Coba dengan password kosong
        try:
            conn = await asyncpg.connect("postgresql://postgres:@localhost:5432/aggregator_db")
            print("[OK] Koneksi berhasil dengan postgres: (password kosong)")
        except Exception as e2:
            print(f"[ERROR] Error dengan password kosong: {e2}")
            
            # Coba dengan postgres:postgres
            try:
                conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/aggregator_db")
                print("[OK] Koneksi berhasil dengan postgres:postgres")
            except Exception as e3:
                print(f"[ERROR] Error dengan postgres:postgres: {e3}")

if __name__ == "__main__":
    asyncio.run(test_connection())