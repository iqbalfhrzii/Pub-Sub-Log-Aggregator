import os
import sys
import asyncio
import asyncpg
import subprocess

async def fix_database():
    """Fix database connection issues"""
    print("Fixing database connection...")
    
    # Test different connection strings
    test_urls = [
        "postgresql://postgres:admin@localhost:5432/aggregator_db",
        "postgresql://postgres:admin@localhost:5432/postgres"
    ]
    
    working_url = None
    
    for url in test_urls:
        try:
            print(f"Testing: {url}")
            conn = await asyncpg.connect(url)
            await conn.close()
            working_url = url
            print(f"[OK] Working URL: {url}")
            break
        except Exception as e:
            print(f"[ERROR] Failed: {e}")
    
    if not working_url:
        print("No working database connection found!")
        return False
    
    # Connect to postgres to create/check aggregator_db
    try:
        conn = await asyncpg.connect("postgresql://postgres:admin@localhost:5432/postgres")
        
        # Drop and recreate database to avoid any issues
        print("Recreating aggregator_db database...")
        await conn.execute("DROP DATABASE IF EXISTS aggregator_db")
        await conn.execute("CREATE DATABASE aggregator_db")
        print("[OK] Database recreated")
        
        await conn.close()
        
        # Connect to new database and create tables
        conn = await asyncpg.connect("postgresql://postgres:admin@localhost:5432/aggregator_db")
        
        print("Creating tables...")
        await conn.execute("""
            CREATE TABLE processed_events (
                id SERIAL PRIMARY KEY,
                topic VARCHAR(255) NOT NULL,
                event_id VARCHAR(255) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                source VARCHAR(255) NOT NULL,
                payload JSONB NOT NULL,
                processed_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(topic, event_id)
            );
            
            CREATE INDEX idx_topic_timestamp ON processed_events(topic, timestamp);
            CREATE INDEX idx_processed_at ON processed_events(processed_at);
            
            CREATE TABLE system_stats (
                id SERIAL PRIMARY KEY,
                received_count BIGINT DEFAULT 0,
                unique_processed_count BIGINT DEFAULT 0,
                duplicate_dropped_count BIGINT DEFAULT 0,
                topics_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW()
            );
            
            INSERT INTO system_stats (received_count, unique_processed_count, duplicate_dropped_count, topics_count)
            VALUES (0, 0, 0, 0);
        """)
        
        await conn.close()
        print("[OK] Tables created successfully")
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        return False

def run_aggregator():
    """Run the aggregator service"""
    print("\nStarting aggregator service...")
    
    # Set clean environment variable
    os.environ["DATABASE_URL"] = "postgresql://postgres:admin@localhost:5432/aggregator_db"
    
    # Change to aggregator directory
    original_dir = os.getcwd()
    os.chdir("aggregator")
    
    try:
        # Run the app
        subprocess.run([sys.executable, "app_simple.py"])
    except KeyboardInterrupt:
        print("\n[OK] Aggregator stopped by user")
    except Exception as e:
        print(f"[ERROR] Aggregator error: {e}")
    finally:
        os.chdir(original_dir)

async def main():
    print("=== UAS System Fix & Run ===\n")
    
    if await fix_database():
        print("\n[OK] Database ready!")
        print("Starting aggregator on http://localhost:8080")
        print("Press Ctrl+C to stop\n")
        run_aggregator()
    else:
        print("\n[ERROR] Database setup failed!")

if __name__ == "__main__":
    asyncio.run(main())