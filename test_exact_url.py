import asyncpg
import asyncio

async def test_exact_url():
    url = "postgresql://postgres:admin@localhost:5432/aggregator_db"
    print(f"Testing connection with URL: {url}")
    
    try:
        conn = await asyncpg.connect(url)
        print("[OK] Connection successful!")
        
        # Test query
        result = await conn.fetchval("SELECT current_database()")
        print(f"[OK] Connected to database: {result}")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print(f"[OK] Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_exact_url())
    if success:
        print("\n[OK] Database is ready for aggregator!")
    else:
        print("\n[ERROR] Database connection failed!")