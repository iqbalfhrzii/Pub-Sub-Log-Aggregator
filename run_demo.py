import os
import sys
import asyncio
import asyncpg
import subprocess
import time

async def setup_database():
    """Setup database dan tabel"""
    print("Setting up database...")
    
    try:
        # Connect ke postgres database
        conn = await asyncpg.connect("postgresql://postgres:admin@localhost:5432/postgres")
        
        # Check if database exists
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'aggregator_db'")
        
        if not db_exists:
            print("Creating aggregator_db database...")
            await conn.execute("CREATE DATABASE aggregator_db")
            print("[OK] Database created")
        else:
            print("[OK] Database already exists")
        
        await conn.close()
        
        # Connect to aggregator_db and create tables
        conn = await asyncpg.connect("postgresql://postgres:admin@localhost:5432/aggregator_db")
        
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
        
        # Insert initial stats if not exists
        await conn.execute("""
            INSERT INTO system_stats (received_count, unique_processed_count, duplicate_dropped_count, topics_count)
            SELECT 0, 0, 0, 0
            WHERE NOT EXISTS (SELECT 1 FROM system_stats);
        """)
        
        await conn.close()
        print("[OK] Tables created and initialized")
        return True
        
    except Exception as e:
        print(f"[ERROR] Database setup failed: {e}")
        return False

def run_aggregator():
    """Run aggregator service"""
    print("Starting aggregator service...")
    
    # Set environment variables
    os.environ["DATABASE_URL"] = "postgresql://postgres:admin@localhost:5432/aggregator_db"
    
    # Change to aggregator directory
    os.chdir("aggregator")
    
    try:
        # Run the simple app
        subprocess.run([sys.executable, "app_simple.py"], check=True)
    except KeyboardInterrupt:
        print("\n[OK] Aggregator stopped by user")
    except Exception as e:
        print(f"[ERROR] Aggregator failed: {e}")

async def main():
    print("=== UAS Pub-Sub Aggregator Demo ===\n")
    
    # Setup database
    if not await setup_database():
        print("Database setup failed. Exiting.")
        return
    
    print("\nDatabase ready! Starting aggregator...")
    print("Press Ctrl+C to stop\n")
    
    # Run aggregator
    run_aggregator()

if __name__ == "__main__":
    asyncio.run(main())