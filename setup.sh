#!/bin/bash

# EPIC-Stroke Data Pipeline Setup Script
# This script helps you set up and run the EPIC-Stroke Data Pipeline

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
echo_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
echo_success() { echo -e "${GREEN}✅ $1${NC}"; }
echo_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
echo_error() { echo -e "${RED}❌ $1${NC}"; }

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create directory if it doesn't exist
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        echo_success "Created directory: $1"
    else
        echo_info "Directory already exists: $1"
    fi
}

echo_info "EPIC-Stroke Data Pipeline Setup"
echo_info "==============================="

# Check prerequisites
echo_info "Checking prerequisites..."

if ! command_exists docker; then
    echo_error "Docker is not installed. Please install Docker first."
    exit 1
fi
echo_success "Docker is installed"

if ! command_exists docker-compose; then
    echo_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
echo_success "Docker Compose is installed"

# Check if Python is available (for testing)
if command_exists python3; then
    echo_success "Python 3 is available"
else
    echo_warning "Python 3 not found. Testing will be limited."
fi

# Create data directory structure
echo_info "Creating data directory structure..."

# Main data directories
create_dir "data"
create_dir "data/EPIC-files"
create_dir "data/sT-files"
create_dir "data/EPIC2sT-pipeline"
create_dir "data/sT-import-validation"
create_dir "data/EPIC-export-validation"
create_dir "data/EPIC-export-validation/validation-files"
create_dir "logs"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo_success "Created .env file from template"
        echo_warning "Please review and update the .env file with your specific configuration"
    else
        echo_warning ".env.template not found. You may need to create a .env file manually"
    fi
else
    echo_info ".env file already exists"
fi

# Create example data structure info
cat > data/README.md << 'EOF'
# Data Directory Structure

This directory contains the data files for the EPIC-Stroke Data Pipeline.

## Expected Structure:

```
data/
├── EPIC-files/
│   └── export-YYYYMMDD/          # EPIC export directories
│       ├── encounters.csv
│       ├── flowsheet.csv
│       ├── imaging.csv
│       ├── lab.csv
│       ├── medication.csv
│       └── monitor.csv
├── sT-files/
│   └── export-YYYYMMDD/          # secuTrial export directories
│       ├── SSR_cases_of_2024.xlsx
│       └── REVASC/
│           └── report_SSR01_*.xlsx
├── EPIC2sT-pipeline/
│   ├── map_epic2sT_code_V2_*.xlsx
│   └── Identification_log_SSR_*.xlsx
└── sT-import-validation/
    └── map_epic2secuTrial_import.xlsx
```

## To use this pipeline:

1. Place your EPIC export files in EPIC-files/export-YYYYMMDD/
2. Place your secuTrial export files in sT-files/export-YYYYMMDD/
3. Place your mapping files in EPIC2sT-pipeline/
4. Run the pipeline with: docker-compose up
EOF

echo_success "Created data directory README"

# Test the setup if Python is available
if command_exists python3; then
    echo_info "Running setup tests..."
    if [ -f "test_setup.py" ]; then
        python3 test_setup.py
    else
        echo_warning "test_setup.py not found. Skipping tests."
    fi
fi

# Build the Docker images
echo_info "Building Docker images..."
if docker-compose build; then
    echo_success "Docker images built successfully"
else
    echo_error "Failed to build Docker images"
    exit 1
fi

# Final instructions
echo_info "Setup complete! Next steps:"
echo ""
echo "1. Place your data files in the appropriate directories under ./data/"
echo "2. Review and update the .env file if needed"
echo "3. Run the pipeline:"
echo "   docker-compose up"
echo ""
echo "To view logs:"
echo "   docker-compose logs validation-service"
echo "   docker-compose logs import-service"
echo ""
echo "To stop the services:"
echo "   docker-compose down"
echo ""
echo_success "Setup completed successfully!"