import asyncpg
import asyncio

async def check_databases():
    try:
        # Connect ke postgres database untuk list databases
        conn = await asyncpg.connect("postgresql://postgres:admin@localhost:5432/postgres")
        
        # List semua databases
        databases = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false;")
        
        print("Available databases:")
        for db in databases:
            print(f"  - {db['datname']}")
        
        # Check apakah aggregator_db ada
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'aggregator_db'")
        
        if not db_exists:
            print("\nCreating aggregator_db database...")
            await conn.execute("CREATE DATABASE aggregator_db")
            print("Database created successfully!")
        else:
            print("\naggregator_db already exists!")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_databases())