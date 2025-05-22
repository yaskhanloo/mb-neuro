# EPIC-secuTrial Validation Service

## Overview

The Enhanced EPIC-secuTrial Validation Service provides comprehensive data quality validation between EPIC exports and secuTrial data. This service has been updated with complete comparison logic from the original notebook to provide detailed validation reports including monthly breakdowns and variable-level statistics.

## Features

### Core Validation Capabilities
- **Comprehensive Data Comparison**: Compares values and data types between EPIC and secuTrial datasets
- **Monthly Statistical Analysis**: Provides month-by-month breakdown of validation results (April-December)
- **Variable-level Statistics**: Detailed analysis of each variable's validation performance
- **Type-aware Comparisons**: Handles different data types appropriately (integers, floats, booleans, dates, strings)
- **Missing Data Analysis**: Identifies and reports missing data patterns in both systems

### Enhanced Reporting
- **Markdown Reports**: Comprehensive validation reports in markdown format
- **Excel Outputs**: Structured Excel files with multiple sheets for different analyses
- **Mismatched Data Restructuring**: Pivoted view of mismatches for easier review
- **Top Problematic Variables**: Identifies variables with highest validation issues

### Data Processing Features
- **Automatic File Detection**: Finds latest export directories automatically
- **Multiple File Format Support**: Handles Excel (.xlsx, .xls) and CSV files
- **Encoding Detection**: Automatically detects file encoding for proper reading
- **Value Mapping**: Applies predefined mappings for consistent data representation
- **Data Type Conversion**: Converts data types according to mapping specifications

## Configuration

The service uses `config/validation_config.yml` for configuration. Key settings include:

```yaml
# Validation settings
compare_values: true
compare_types: true
generate_report: true
include_monthly_breakdown: true
include_variable_statistics: true

# Report formats
report_format: markdown
save_individual_reports: true
save_summary_statistics: true
```

## Input Files Required

### Directory Structure
```
data/
├── sT-files/
│   └── export-YYYYMMDD/
│       ├── SSR_cases_of_2024.xlsx
│       └── REVASC/
│           └── report_SSR01_YYYYMMDD-HHMMSS.xlsx
├── EPIC-files/
│   └── export-YYYYMMDD/
│       ├── encounters.csv
│       ├── flowsheet.csv
│       ├── imaging.csv
│       ├── lab.csv
│       ├── medication.csv
│       └── monitor.csv
└── EPIC2sT-pipeline/
    ├── map_epic2sT_code_V2_YYYYMMDD.xlsx
    └── Identification_log_SSR_2024_ohne PW_DDMMYY.xlsx
```

### Required Files
1. **secuTrial Export**: `SSR_cases_of_2024.xlsx`
2. **REVASC Data**: `report_SSR01_YYYYMMDD-HHMMSS.xlsx`
3. **EPIC Files**: Multiple CSV files (encounters, flowsheet, imaging, lab, medication, monitor)
4. **Mapping File**: `map_epic2sT_code_V2_YYYYMMDD.xlsx`
5. **ID Log**: `Identification_log_SSR_2024_ohne PW_DDMMYY.xlsx`

## Output Files

### Generated Reports
- **Validation Report**: `validation_report_YYYYMMDD_HHMMSS.md`
- **Mismatched Values**: `report_mismatched_values_YYYYMMDD_HHMMSS.xlsx`
- **Monthly Statistics**: `monthly_validation_stats_YYYYMMDD_HHMMSS.xlsx`
- **Original Data**: `df_EPIC_common_YYYYMMDD_HHMMSS.xlsx` and `df_secuTrial_common_YYYYMMDD_HHMMSS.xlsx`

### Report Contents

#### Validation Report (Markdown)
- Overall statistics summary
- Monthly breakdown of validation results
- Top 10 most problematic variables
- Variables with type mismatches
- Detailed analysis and recommendations

#### Monthly Statistics (Excel)
- **Monthly_Stats Sheet**: Month-by-month validation performance
- **Overall_Stats Sheet**: Complete summary statistics
- **Variable_Stats Sheet**: Per-variable validation results

#### Mismatched Values (Excel)
- Restructured view of all mismatched values
- One row per patient (FID/SSR combination)
- Side-by-side comparison of EPIC vs secuTrial values

## Usage

### Running with Docker
```bash
# Build and start the validation service
docker-compose up -d validation-service

# Check logs
docker-compose logs -f validation-service

# Stop the service
docker-compose stop validation-service
```

### Running Locally
```bash
# Set up environment
export PYTHONPATH=.
export BASE_DIR=./data

# Run the validation service
python validation-service/src/main.py
```

## Key Statistics Tracked

### Overall Statistics
- **Total Comparisons**: Number of field-level comparisons performed
- **Matching Variables**: Fields with identical values between systems
- **Mismatched Variables**: Fields with different values between systems
- **Variables Missing in EPIC**: Fields present in secuTrial but not EPIC
- **Variables Missing in secuTrial**: Fields present in EPIC but not secuTrial

### Monthly Breakdown
- Month-by-month analysis for April through December
- Percentage breakdowns for each validation category
- Identification of seasonal patterns in data quality

### Variable-level Analysis
- Per-variable validation performance
- Identification of most problematic variables
- Data type compatibility analysis
- Missing data patterns by variable

## Data Validation Logic

### Value Comparison
- **Exact Matches**: String values compared case-insensitively
- **Numeric Tolerance**: Floating-point comparisons with epsilon tolerance
- **Boolean Standardization**: Converts various boolean representations to "yes/no"
- **Date Formatting**: Standardizes date formats before comparison
- **Missing Value Handling**: Treats various missing value indicators consistently

### Data Type Handling
- **Type Coercion**: Converts values to appropriate types before comparison
- **Precision Handling**: Respects decimal precision specifications (e.g., float-2)
- **Boolean Standardization**: Normalizes boolean values across systems
- **Date Parsing**: Handles multiple date formats automatically

### Value Mappings
- **Coded Values**: Maps numeric codes to descriptive text
- **Boolean Values**: Standardizes true/false representations
- **Categorical Data**: Maps between different category systems
- **Custom Mappings**: Applies domain-specific value transformations

## Troubleshooting

### Common Issues

#### Missing Files
```
ERROR: Required secuTrial file not found: /app/data/sT-files/export-YYYYMMDD/SSR_cases_of_2024.xlsx
```
**Solution**: Ensure all required files are present in the correct directory structure.

#### Encoding Issues
```
WARNING: Failed with encoding utf-8: 'utf-8' codec can't decode byte 0xf6
```
**Solution**: The service automatically tries multiple encodings. Check file integrity if issues persist.

#### Missing Columns
```
ERROR: EPIC DataFrame must contain 'enct.arrival_date' column for monthly breakdown
```
**Solution**: Check that the EPIC files contain the expected columns and the merge process completed successfully.

### Performance Optimization

#### Large Datasets
- The service automatically handles large datasets through chunking
- Monitor memory usage if processing very large files
- Consider running on machines with sufficient RAM

#### File Processing
- CSV files are processed with automatic encoding detection
- Tab-delimited files are handled automatically
- Multiple delimiter types are tried if standard parsing fails

## Logging

The service provides comprehensive logging:
- **INFO**: General progress and status updates
- **WARNING**: Non-critical issues that don't stop processing
- **ERROR**: Critical issues that require attention

Log files are saved to `/app/data/logs/validation_service_YYYYMMDD_HHMMSS.log`

## Contributing

When modifying the validation service:
1. Update the appropriate configuration files
2. Add new value mappings to the config as needed
3. Update tests for new functionality
4. Document any new features or changes

## Integration with Other Services

The validation service integrates with:
- **Import Service**: Uses similar data processing logic
- **Model Loader**: Leverages JavaScript model definitions
- **Value Mapper**: Applies consistent value transformations

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify input file structure and content
3. Review configuration settings
4. Test with a smaller dataset if issues persist