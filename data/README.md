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
