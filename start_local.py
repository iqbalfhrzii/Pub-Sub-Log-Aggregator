import os
import sys
import subprocess

# Set environment variables
os.environ["DATABASE_URL"] = "postgresql://postgres:admin@localhost:5432/aggregator_db"
os.environ["REDIS_URL"] = "redis://localhost:6379"

print("Starting UAS Aggregator locally...")
print(f"Database URL: {os.environ['DATABASE_URL']}")
print(f"Redis URL: {os.environ['REDIS_URL']}")

# Change to aggregator directory
os.chdir("aggregator")

# Run the app
try:
    subprocess.run([sys.executable, "app.py"], check=True)
except KeyboardInterrupt:
    print("\nShutting down...")
except Exception as e:
    print(f"Error: {e}")