#!/usr/bin/env python3
"""
Script untuk menjalankan tests sistem UAS
"""

import subprocess
import sys
import time
import requests
import os

def wait_for_service(url, max_retries=30):
    """Wait untuk service ready"""
    print(f"Waiting for service at {url}...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✓ Service ready at {url}")
                return True
        except:
            pass
        print(f"  Attempt {i+1}/{max_retries}...")
        time.sleep(2)
    
    print(f"✗ Service not ready at {url}")
    return False

def run_command(cmd, cwd=None):
    """Run command dan return success status"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {cmd}")
            return True
        else:
            print(f"✗ {cmd}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ {cmd} - Exception: {e}")
        return False

def main():
    print("=== UAS Sistem Terdistribusi - Test Runner ===\n")
    
    # Check if Docker Compose is running
    print("1. Checking Docker Compose status...")
    if not run_command("docker compose ps"):
        print("Starting Docker Compose...")
        if not run_command("docker compose up -d --build"):
            print("Failed to start Docker Compose")
            return False
    
    # Wait for services
    print("\n2. Waiting for services to be ready...")
    if not wait_for_service("http://localhost:8080"):
        print("Aggregator service not ready")
        return False
    
    # Install test dependencies
    print("\n3. Installing test dependencies...")
    if not run_command("pip install pytest requests"):
        print("Failed to install dependencies")
        return False
    
    # Run tests
    print("\n4. Running tests...")
    test_cmd = "python -m pytest tests/test_system.py -v --tb=short"
    
    if run_command(test_cmd):
        print("\n✓ All tests completed successfully!")
        
        # Show final stats
        print("\n5. Final system statistics:")
        try:
            response = requests.get("http://localhost:8080/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                print(f"  Received events: {stats.get('received_count', 0)}")
                print(f"  Unique processed: {stats.get('unique_processed_count', 0)}")
                print(f"  Duplicates dropped: {stats.get('duplicate_dropped_count', 0)}")
                print(f"  Topics: {stats.get('topics_count', 0)}")
                print(f"  Uptime: {stats.get('uptime_seconds', 0)} seconds")
        except Exception as e:
            print(f"Could not fetch stats: {e}")
        
        return True
    else:
        print("\n✗ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)