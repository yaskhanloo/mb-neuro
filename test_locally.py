#!/usr/bin/env python3
"""
Local testing script for validation service
Test each component step by step before Docker
"""

import os
import sys
from pathlib import Path

# Set up environment for local testing
print("🧪 Setting up local testing environment...")

# Set BASE_DIR for local testing (adjust this path to your data directory)
LOCAL_DATA_DIR = Path("./data")  # Change this to your actual data directory
os.environ['BASE_DIR'] = str(LOCAL_DATA_DIR)

print(f"📁 Using data directory: {LOCAL_DATA_DIR}")
print(f"🔍 Directory exists: {LOCAL_DATA_DIR.exists()}")

if not LOCAL_DATA_DIR.exists():
    print("❌ Data directory not found! Please create it or adjust LOCAL_DATA_DIR")
    print("Expected structure:")
    print("  data/")
    print("    ├── EPIC-files/export-YYYYMMDD/")
    print("    ├── sT-files/export-YYYYMMDD/")
    print("    └── EPIC2sT-pipeline/")
    sys.exit(1)

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

print("🚀 Starting validation service...")
print("-" * 50)

try:
    # Import and run main
    from validation_service.src.main import main
    main()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have the correct directory structure:")
    print("  validation-service/")
    print("    └── src/")
    print("        ├── main.py")
    print("        ├── utils/")
    print("        └── processors/")
    
except Exception as e:
    print(f"❌ Error during execution: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("🏁 Local testing completed!")
print("Check the logs directory for detailed output.")