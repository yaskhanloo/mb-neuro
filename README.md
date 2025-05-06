# EPIC-Stroke Data Pipeline

This repository contains two microservices for validating and importing EPIC data into secuTrial:

1. **EPIC Validation Service**: Validates EPIC exports against secuTrial data.
2. **EPIC Import Service**: Merges EPIC data with secuTrial data and generates CSV files for import.

```
docker-compose down
docker-compose build
docker-compose up -d

docker-compose logs validation-service
docker-compose logs import-service

```

## Prerequisites

- Docker and Docker Compose
- secuTrial export files

## Directory Structure

Place your data files in the following structure:

```
data/
├── sT-files/
│   └── export-/ (secuTrial export directories)
├── EPIC-files/
│   └── export-/ (EPIC export directories) - will change 
└── EPIC2sT-pipeline/
    ├── map_epic2sT_code_V2_20250224.xlsx
    └── Identification_log_SSR_2024_ohne PW_26.03.25.xlsx
```

## Running the Services with Docker

1. **Build and start the services**:

```bash
docker-compose up -d
```

2. **Check logs**:

- Validation Service:
  ```bash
  docker-compose logs validation-service
  ```

- Import Service:
  ```bash
  docker-compose logs import-service
  ```

3. **Access the output files**:

- Validation reports: `data/validation-files/`
- Import files: `data/import-files/`

## Configuration

Adjust service configuration files located in the `config/` directory:

- `validation_config.yml`: EPIC Validation Service settings
- `import_config.yml`: EPIC Import Service settings

Additionally, create an `.env` file in your project's root directory to manage database connections:

**`.env`**:

```
NODE_ENV=development
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=medical-server
DB_USER=root
DB_PASSWORD=ServeMySql2009Secure
```

## Development Workflow and CI/CD - not there yet

This repository includes automated CI/CD using GitHub Actions. Configuration details are available in:

**`.github/workflows/ci-cd.yml`**

The pipeline performs:

- Dependency installation
- Linting with `flake8`
- Testing with `pytest` and coverage reporting
- Docker image building and publishing to DockerHub (on main branch)

Ensure secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) are configured in your GitHub repository settings.

## Schedule-Based Automation

Automate periodic execution of validation and import processes by creating a cron job script:

**`automation/run_pipeline.sh`**

---

## Testing Without Docker

1. **Set up a Python virtual environment**:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**:

```bash
pip install -r validation-service/requirements.txt
pip install -r import-service/requirements.txt
```

3. **Run services locally**:

```bash
export PYTHONPATH=.
python validation-service/src/main.py
python import-service/src/main.py
```