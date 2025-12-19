import os
import sys
import subprocess

def run_aggregator():
    """Run aggregator with proper environment"""
    print("=== Starting UAS Aggregator ===")
    
    # Set environment variable
    os.environ["DATABASE_URL"] = "postgresql://postgres:admin@localhost:5432/aggregator_db"
    
    print("Database URL:", os.environ["DATABASE_URL"])
    print("Starting on http://localhost:8081")
    print("Press Ctrl+C to stop\n")
    
    # Change to aggregator directory
    original_dir = os.getcwd()
    os.chdir("aggregator")
    
    try:
        # Run the app
        subprocess.run([sys.executable, "app_simple.py"])
    except KeyboardInterrupt:
        print("\n[OK] Stopped by user")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    run_aggregator()