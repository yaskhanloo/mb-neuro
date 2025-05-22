#!/usr/bin/env python3
"""
Test script to verify the EPIC-Stroke Data Pipeline setup
"""

import os
import sys
from pathlib import Path
import logging

def setup_test_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger('setup-test')

def test_directory_structure():
    """Test if required directories exist"""
    logger = setup_test_logging()
    
    required_dirs = [
        "data/EPIC-files",
        "data/sT-files",
        "data/EPIC2sT-pipeline", 
        "data/sT-import-validation",
        "data/EPIC-export-validation/validation-files",
        "validation-service/src",
        "import-service/src",
        "shared"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        logger.error(f"❌ Missing directories: {missing_dirs}")
        return False
    else:
        logger.info("✅ All required directories exist")
        return True

def test_docker_files():
    """Test if Docker setup is correct"""
    logger = setup_test_logging()
    
    required_files = [
        "docker-compose.yml",
        "validation-service/Dockerfile",
        "validation-service/requirements.txt",
        "import-service/Dockerfile", 
        "import-service/requirements.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        return False
    else:
        logger.info("✅ All required Docker files exist")
        return True

def test_python_services():
    """Test if the Python services exist and are readable"""
    logger = setup_test_logging()
    
    service_files = [
        "validation-service/src/main.py",
        "import-service/src/main.py"
    ]
    
    for service_file in service_files:
        if not Path(service_file).exists():
            logger.error(f"❌ Missing service file: {service_file}")
            return False
        
        try:
            with open(service_file, 'r') as f:
                content = f.read()
                if len(content) < 100:  # Basic sanity check
                    logger.error(f"❌ Service file seems too short: {service_file}")
                    return False
        except Exception as e:
            logger.error(f"❌ Cannot read service file {service_file}: {e}")
            return False
    
    logger.info("✅ Python service files exist and are readable")
    return True

def main():
    """Run all tests"""
    logger = setup_test_logging()
    logger.info("🧪 Starting EPIC-Stroke Data Pipeline Setup Test")
    
    tests = [
        ("Directory Structure", test_directory_structure),
        ("Docker Files", test_docker_files), 
        ("Python Services", test_python_services)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n=== Testing {test_name} ===")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with error: {e}")
            results.append(False)
    
    # Summary
    logger.info("\n=== Test Summary ===")
    if all(results):
        logger.info("🎉 All tests passed! Setup looks good.")
        logger.info("\nNext steps:")
        logger.info("1. Make sure Docker Desktop is running")
        logger.info("2. Run: docker-compose up --build")
        logger.info("3. Check logs: docker-compose logs")
        return True
    else:
        logger.error("❌ Some tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)