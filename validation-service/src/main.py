#!/usr/bin/env python3
"""
EPIC-secuTrial Validation Service
Simple main script converted from validation_EPIC2sT_V1_20250522.ipynb

Created by: Yasaman Safarkhanlo
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import chardet
import logging
import re
import io
from typing import Dict, Any, Optional, Tuple, List, Union

# Global logger
logger = None

def setup_logging():
    """Configure logging for the application"""
    # Detect environment: if running in Docker, use /app/data/logs; else, use ./logs
    base_dir = os.getenv('BASE_DIR', '.')
    log_dir = Path(base_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"validation_service_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger('epic-validation')

def read_and_modify_secuTrial_export(df):
    """
    Process secuTrial export dataframe by removing metadata rows and setting proper headers.
    """
    try:
        return (df.iloc[6:]
                 .pipe(lambda x: x.set_axis(x.iloc[0], axis=1))
                 .iloc[1:]
                 .reset_index(drop=True)
                 .dropna(how='all'))
    except Exception as e:
        logger.error(f"Error processing secuTrial export: {e}")
        return df

def safe_read_file(file_path, custom_reader=None):
    """
    Safely reads a file (Excel or CSV), with an option for a custom reader function.
    """
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()

    try:
        if file_extension in [".xlsx", ".xls"]:
            if custom_reader:
                df = pd.read_excel(file_path, engine='openpyxl' if file_extension == ".xlsx" else 'xlrd', header=None)
            else:
                df = pd.read_excel(file_path, engine='openpyxl' if file_extension == ".xlsx" else 'xlrd')
        elif file_extension == ".csv":
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
            separators = [',', '\t', ';', '|']
            df = None
            for encoding in encodings:
                for sep in separators:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep, on_bad_lines='skip')
                        if len(df.columns) > 1:  # Good separator found
                            break
                    except:
                        continue
                if df is not None and len(df.columns) > 1:
                    break
            if df is None:
                # Fallback to simple CSV read
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except:
                    raise ValueError("Could not read CSV with any encoding or separator")
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        result = custom_reader(df) if custom_reader else df

        if result is None or result.empty:
            logger.warning(f"{file_path.name} is empty after processing.")
            return None

        return result

    except FileNotFoundError:
        logger.error(f"File not found at {file_path}")
    except Exception as e:
        logger.error(f"Error reading file at {file_path}: {e}")
    
    return None

def merge_single_epic_file(file_path, merge_column, merged_df, prefix=""):
    """
    Merge a single EPIC file into the main DataFrame with optional column prefixing.
    """
    df = safe_read_file(file_path)
    if df is None:
        logger.warning(f"Failed to read {file_path.name}")
        return merged_df

    if merge_column not in df.columns:
        logger.warning(f"Merge column '{merge_column}' not found in {file_path.name}")
        return merged_df

    # Add prefix to all columns except the merge column
    if prefix:
        df = df.rename(columns={col: f"{prefix}{col}" for col in df.columns if col != merge_column})

    # Merge logic
    if merged_df.empty:
        result_df = df.copy()
        logger.info(f"Using {file_path.name} as base: shape={result_df.shape}")
    else:
        result_df = merged_df.merge(df, on=merge_column, how="outer")
        logger.info(f"Merged {file_path.name}: shape={df.shape} → total={result_df.shape}")

    return result_df

def find_merge_column(directory):
    """Find the correct merge column by checking the first file"""
    directory = Path(directory)
    file_patterns = ["*.xlsx", "*.xls", "*.csv"]
    all_files = [f for pattern in file_patterns for f in directory.glob(pattern)]
    
    if not all_files:
        return None
        
    # Check first file for common merge columns
    first_file = all_files[0]
    df = safe_read_file(first_file)
    if df is not None and len(df.columns) > 1:
        possible_columns = ['PAT_ENC_CSN_ID', 'PatientID', 'ID', 'Patient_ID', 'CSN_ID']
        for col in possible_columns:
            if col in df.columns:
                logger.info(f"Found merge column: {col}")
                return col
        
        logger.info(f"Available columns in {first_file.name}: {list(df.columns)}")
        # Return the first column that looks like an ID
        for col in df.columns:
            if any(word in col.upper() for word in ['ID', 'CSN', 'PATIENT']):
                logger.info(f"Using merge column: {col}")
                return col
    
    return 'PAT_ENC_CSN_ID'  # Default fallback

def merge_all_epic_files(directory, merge_column=None):
    """
    Merges all EPIC files in a directory based on a specific column, in a defined order.
    """
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        raise FileNotFoundError(f"{directory} does not exist.")

    file_patterns = ["*.xlsx", "*.xls", "*.csv"]
    all_files = [f for pattern in file_patterns for f in directory.glob(pattern)]
    logger.info(f"Found {len(all_files)} data files in {directory.name}")

    # Auto-detect merge column if not provided
    if merge_column is None:
        merge_column = find_merge_column(directory)
        if merge_column is None:
            logger.error("Could not find a suitable merge column")
            return pd.DataFrame()

    file_order = ['enc', 'flow', 'imag', 'img', 'lab', 'med', 'mon']

    def file_priority(file_path):
        name = file_path.stem.lower()
        for i, keyword in enumerate(file_order):
            if keyword in name:
                return i
        return len(file_order)

    def get_prefix(filename):
        name = filename.lower()
        if 'enc' in name: return 'enct.'
        if 'flow' in name: return 'flow.'
        if 'imag' in name or 'img' in name: return 'img.'
        if 'lab' in name: return 'lab.'
        if 'med' in name: return 'med.'
        if 'mon' in name: return 'mon.'
        return ""

    sorted_files = sorted(all_files, key=file_priority)

    merged_df = pd.DataFrame()
    for file_path in sorted_files:
        prefix = get_prefix(file_path.stem)
        merged_df = merge_single_epic_file(file_path, merge_column, merged_df, prefix)
    return merged_df

def merge_secuTrial_with_REVASC(df_secuTrial, df_REVASC, logger):
    """Merge REVASC data into secuTrial DataFrame."""
    try:
        merged_df = df_secuTrial.merge(
            df_REVASC,
            how='left',
            left_on='Case ID',
            right_on='CaseID',
            suffixes=('', '.revas')
        )
        merged_df.drop(columns=['CaseID'], inplace=True, errors='ignore')
        merged_df.reset_index(drop=True, inplace=True)
        
        logger.info(f"Successfully merged secuTrial + REVASC: {merged_df.shape}")
        return merged_df
        
    except Exception as e:
        logger.error(f"REVASC merge failed: {e}. Using secuTrial data only.")
        return df_secuTrial.copy()
    
def load_and_process_id_log(id_log_path, logger):
    """Load and process the ID log file."""
    try:
        id_log = pd.read_excel(id_log_path)
        logger.info(f"ID log original columns: {list(id_log.columns)}")
        
        # Set first row as headers
        id_log.columns = id_log.iloc[0]
        id_log = id_log.iloc[1:].reset_index(drop=True)
        logger.info(f"ID log columns after header fix: {list(id_log.columns)}")
        
        # Map the actual column names we found
        column_mapping = {}
        for col in id_log.columns:
            if pd.isna(col):  # Skip NaN columns
                continue
            col_str = str(col).strip()
            if 'Fall-Nr.' in col_str:
                column_mapping[col] = 'FID'
            elif 'SSR Identification' in col_str:
                column_mapping[col] = 'SSR'
        
        logger.info(f"Column mapping: {column_mapping}")
        id_log.rename(columns=column_mapping, inplace=True)
        
        # Remove NaN columns
        id_log = id_log.loc[:, ~id_log.columns.isna()]
        
        # Check if we have the required columns
        if 'FID' not in id_log.columns or 'SSR' not in id_log.columns:
            logger.error(f"Required columns not found. Available: {list(id_log.columns)}")
            logger.error("Expected to find 'Fall-Nr.' and 'SSR Identification' columns")
            return None
            
        # Convert to appropriate data types
        id_log['FID'] = pd.to_numeric(id_log['FID'], errors='coerce')
        id_log['SSR'] = pd.to_numeric(id_log['SSR'], errors='coerce')
        
        # Remove rows with missing FID or SSR
        initial_count = len(id_log)
        id_log = id_log.dropna(subset=['FID', 'SSR'])
        final_count = len(id_log)
        
        if final_count < initial_count:
            logger.warning(f"Removed {initial_count - final_count} rows with missing FID/SSR")
            
        logger.info(f"Loaded ID log with {final_count} valid entries")
        return id_log
    except Exception as e:
        logger.error(f"Failed to load ID log: {e}")
        return None

def add_patient_ids(df_epic, df_secuTrial, id_log, logger):
    """Add FID and SSR columns to both dataframes."""
    
    # Add FID to EPIC data
    if 'img.FID' in df_epic.columns:
        df_epic['FID'] = df_epic['img.FID'].fillna(0).astype(int)
        df_epic.insert(0, 'FID', df_epic.pop('FID'))
        logger.info("Added FID to EPIC data")
    else:
        logger.warning("img.FID column not found in EPIC data")
    
    # Add SSR to secuTrial data
    if 'Case ID' in df_secuTrial.columns:
        df_secuTrial['SSR'] = df_secuTrial['Case ID'].str.extract(r'(\d+)$').astype(int)
        df_secuTrial.insert(1, 'SSR', df_secuTrial.pop('SSR'))
        # Clean up any 'nan' columns
        df_secuTrial = df_secuTrial.drop(columns=['nan'], errors='ignore')
        logger.info("Added SSR to secuTrial data")
    else:
        logger.warning("Case ID column not found in secuTrial data")
    
    # Merge with ID log
    if id_log is not None:
        # Check if required columns exist in ID log
        if 'FID' not in id_log.columns:
            logger.error(f"FID column not found in ID log. Available columns: {list(id_log.columns)}")
            return df_epic, df_secuTrial
            
        if 'SSR' not in id_log.columns:
            logger.error(f"SSR column not found in ID log. Available columns: {list(id_log.columns)}")
            return df_epic, df_secuTrial
        
        # Merge EPIC with ID log
        if 'FID' in df_epic.columns:
            df_epic = df_epic.merge(id_log[['FID', 'SSR']], on='FID', how='left')
            df_epic.insert(1, 'SSR', df_epic.pop('SSR'))
            logger.info("Merged EPIC with ID log")
        
        # Merge secuTrial with ID log  
        if 'SSR' in df_secuTrial.columns:
            df_secuTrial = df_secuTrial.merge(id_log[['SSR', 'FID']], on='SSR', how='left')
            df_secuTrial.insert(0, 'FID', df_secuTrial.pop('FID'))
            logger.info("Merged secuTrial with ID log")
        
        logger.info("Successfully added patient IDs to both dataframes")
    
    return df_epic, df_secuTrial

def find_matching_patients(df_epic, df_secuTrial, logger):
    """Find patients that exist in both datasets."""
    
    # Find common patients by FID and SSR
    common_keys = df_secuTrial[['FID', 'SSR']].merge(
        df_epic[['FID', 'SSR']], 
        on=['FID', 'SSR'], 
        how='inner'
    )
    
    # Filter to matching patients only
    df_epic_common = df_epic.merge(common_keys, on=['FID', 'SSR'], how='inner')
    df_secuTrial_common = df_secuTrial.merge(common_keys, on=['FID', 'SSR'], how='inner')
    
    logger.info(f"Found {len(common_keys)} matching patients")
    logger.info(f"EPIC common shape: {df_epic_common.shape}")
    logger.info(f"secuTrial common shape: {df_secuTrial_common.shape}")
    
    return df_epic_common, df_secuTrial_common

def find_missing_patients(df_epic, df_secuTrial, logger):
    """Find patients that exist in only one dataset."""
    
    # Patients only in secuTrial
    df_secuTrial_only = df_secuTrial.merge(
        df_epic[['FID', 'SSR']], 
        on=['FID', 'SSR'], 
        how='left', 
        indicator=True
    ).query('_merge == "left_only"').drop(columns=['_merge'])
    
    # Patients only in EPIC
    df_epic_only = df_epic.merge(
        df_secuTrial[['FID', 'SSR']], 
        on=['FID', 'SSR'], 
        how='left', 
        indicator=True
    ).query('_merge == "left_only"').drop(columns=['_merge'])
    
    logger.info(f"Patients only in secuTrial: {len(df_secuTrial_only)}")
    logger.info(f"Patients only in EPIC: {len(df_epic_only)}")
    
    return df_secuTrial_only, df_epic_only

def save_patient_analysis(df_epic_common, df_secuTrial_common, 
                         df_epic_only, df_secuTrial_only, output_dir, logger):
    """Save patient matching analysis to Excel files."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save common patients
    common_file = output_dir / f"common_patients_{timestamp}.xlsx"
    with pd.ExcelWriter(common_file) as writer:
        df_secuTrial_common.to_excel(writer, sheet_name="secuTrial_common", index=False)
        df_epic_common.to_excel(writer, sheet_name="EPIC_common", index=False)
    
    # Save missing patients (with only relevant columns)
    missing_file = output_dir / f"missing_patients_{timestamp}.xlsx"
    
    # Select relevant columns for comparison
    secuTrial_cols = ['FID', 'SSR', 'Last name', 'First name', 'DOB', 'Arrival at hospital']
    epic_cols = ['FID', 'SSR', 'enct.name_last', 'enct.name_first', 'enct.birth_date', 'enct.arrival_date']
    
    # Only include columns that exist
    secuTrial_subset = df_secuTrial_only[[col for col in secuTrial_cols if col in df_secuTrial_only.columns]]
    epic_subset = df_epic_only[[col for col in epic_cols if col in df_epic_only.columns]]
    
    with pd.ExcelWriter(missing_file) as writer:
        secuTrial_subset.to_excel(writer, sheet_name="only_in_secuTrial", index=False)
        epic_subset.to_excel(writer, sheet_name="only_in_EPIC", index=False)
    
    logger.info(f"Patient analysis saved to {common_file} and {missing_file}")
    
    return df_epic_common, df_secuTrial_common

def process_patient_matching(df_epic, df_secuTrial, id_log_path, output_dir, logger):
    """
    Complete patient matching workflow.
    
    Returns:
        tuple: (df_epic_common, df_secuTrial_common) - datasets with only matching patients
    """
    
    # Load ID log
    id_log = load_and_process_id_log(id_log_path, logger)
    if id_log is None:
        return df_epic, df_secuTrial  # Return original data if ID log fails
    
    # Add patient IDs
    df_epic, df_secuTrial = add_patient_ids(df_epic, df_secuTrial, id_log, logger)
    
    # Find matching and missing patients
    df_epic_common, df_secuTrial_common = find_matching_patients(df_epic, df_secuTrial, logger)
    df_secuTrial_only, df_epic_only = find_missing_patients(df_epic, df_secuTrial, logger)
    
    # Save analysis
    df_epic_common, df_secuTrial_common = save_patient_analysis(
        df_epic_common, df_secuTrial_common, 
        df_epic_only, df_secuTrial_only, 
        output_dir, logger
    )
    
    return df_epic_common, df_secuTrial_common

def main():
    """Main function"""
    global logger
    logger = setup_logging()
    
    logger.info("Starting EPIC-secuTrial Validation Service")
    
    # Use environment variable for base directory with fallback
    base_dir = Path(os.environ.get("BASE_DIR", "."))
    logger.info(f"Using base directory: {base_dir}")
    
    try:
        # Find latest export folders
        latest_sT_export = max((base_dir / "sT-files").glob("export-*"), 
                             key=lambda x: x.stat().st_mtime, default=None)
        latest_EPIC_export = max((base_dir / "EPIC-files").glob("export-*"), 
                               key=lambda x: x.stat().st_mtime, default=None)

        if latest_sT_export:
            secuTrial_base_dir = latest_sT_export
            REVASC_base_dir = secuTrial_base_dir / "REVASC"
            logger.info(f"Latest secuTrial export found: {secuTrial_base_dir}")
        else:
            logger.error("No valid secuTrial export directory found.")
            return

        if latest_EPIC_export:
            epic_base_dir = latest_EPIC_export
            logger.info(f"Latest EPIC export found: {epic_base_dir}")
        else:
            logger.error("No valid EPIC export directory found.")
            return

        # Define file paths
        file_path_secuTrial = secuTrial_base_dir / 'SSR_cases_of_2024.xlsx'
        file_path_REVASC = REVASC_base_dir / 'report_SSR01_20250218-105747.xlsx'

        # Read files
        logger.info("Loading secuTrial data...")
        df_secuTrial = safe_read_file(file_path_secuTrial, custom_reader=read_and_modify_secuTrial_export)
        
        logger.info("Loading REVASC data...")
        df_REVASC = safe_read_file(file_path_REVASC, custom_reader=read_and_modify_secuTrial_export)

        # Log data frame sizes
        if df_secuTrial is not None and df_REVASC is not None:
            logger.info(f"Data loaded successfully: secuTrial={df_secuTrial.shape}, REVASC={df_REVASC.shape}")
        else:
            logger.warning("One or more dataframes failed to load.")
            return

        # Merge all EPIC files
        logger.info("Starting to merge files...")
        df_EPIC_all = merge_all_epic_files(epic_base_dir)  # Auto-detect merge column
        df_secuTrial_w_REVAS = merge_secuTrial_with_REVASC(df_secuTrial, df_REVASC, logger)
        
        if not df_EPIC_all.empty:
            logger.info(f"Final merged EPIC DataFrame shape: {df_EPIC_all.shape}")
            
            # Save merged data for reference
            output_dir = base_dir / "EPIC-export-validation/validation-files"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"merged_epic_data_{timestamp}.csv"
            df_EPIC_all.to_csv(output_path, index=False)
            logger.info(f"Merged EPIC data saved to: {output_path}")
        else:
            logger.warning("Merged EPIC DataFrame is empty.")
            return

        # Process patient matching
        logger.info("Starting patient matching process...")
        
        # Set up paths
        output_dir = base_dir / 'EPIC-export-validation/validation-files'
        id_log_path = base_dir / 'EPIC2sT-pipeline/Identification_log_SSR_2024_ohne PW_26.03.25.xlsx'
        
        # Process patient matching and get only matching patients
        df_epic_common, df_secuTrial_common = process_patient_matching(
            df_EPIC_all, 
            df_secuTrial_w_REVAS, 
            id_log_path, 
            output_dir, 
            logger
        )
        
        logger.info("Patient matching completed successfully!")
        logger.info(f"Common patients - EPIC: {df_epic_common.shape}, secuTrial: {df_secuTrial_common.shape}")

        # TODO: Add comparison logic here
        logger.info("Data loading completed successfully!")
        logger.info("Next step: Implement comparison logic")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        raise

if __name__ == "__main__":
    main()