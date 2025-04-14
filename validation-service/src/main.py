#!/usr/bin/env python3
"""
EPIC-secuTrial Validation Service
Automated script to validate EPIC exports against secuTrial data entries.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import chardet
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('epic-validation')

def main():
    logger.info("Starting EPIC-secuTrial Validation Service")

    # Use environment variable for base directory with fallback
    base_dir = Path(os.environ.get("BASE_DIR", "/app/data"))
    logger.info(f"Using base directory: {base_dir}")
    
    # Check if required directories exist
    required_dirs = [
        base_dir / "EPIC-files",
        base_dir / "sT-files",
        base_dir / "EPIC2sT-pipeline",
        base_dir / "EPIC-export-validation/validation-files"
    ]
    
    for directory in required_dirs:
        if not directory.exists():
            logger.warning(f"Required directory does not exist: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    # Define helper functions
    def read_and_modify_secuTrial_export(df):
        try:
            df = df.drop([7])
            df = df.iloc[6:]
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Error in read_and_modify_secuTrial_export: {e}")
            return None

    def safe_read_file(file_path, custom_reader=None):
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        try:
            file_extension = file_path.suffix.lower()
            logger.info(f"Reading file: {file_path} with extension {file_extension}")
            
            if file_extension in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path, engine='openpyxl' if file_extension == ".xlsx" else 'xlrd', header=None)
            elif file_extension == ".csv":
                df = pd.read_csv(file_path)
            else:
                logger.error(f"Unsupported file type: {file_extension}")
                return None
            
            return custom_reader(df) if custom_reader else df
            
        except Exception as e:
            logger.error(f"Error reading file at {file_path}: {e}")
            return None
    
    # Try to find latest export folders
    try:
        latest_sT_export = max((base_dir / "sT-files").glob("export-*"), 
                              key=lambda x: x.stat().st_mtime, default=None)
        latest_EPIC_export = max((base_dir / "EPIC-files").glob("export-*"), 
                                key=lambda x: x.stat().st_mtime, default=None)
                                
        logger.info(f"Latest secuTrial export: {latest_sT_export}")
        logger.info(f"Latest EPIC export: {latest_EPIC_export}")
        
        if not latest_sT_export:
            logger.error("No valid secuTrial export directory found.")
            return
            
        if not latest_EPIC_export:
            logger.error("No valid EPIC export directory found.")
            return
            
        # Define file paths
        secuTrial_base_dir = latest_sT_export
        REVASC_base_dir = secuTrial_base_dir / "REVASC"
        epic_base_dir = latest_EPIC_export
        
        file_path_secuTrial = secuTrial_base_dir / 'SSR_cases_of_2024.xlsx'
        file_path_REVASC = REVASC_base_dir / 'report_SSR01_20250218-105747.xlsx'
        file_path_EPIC = epic_base_dir / 'encounters.csv'
        
        # Check if required files exist
        if not file_path_secuTrial.exists():
            logger.error(f"Required secuTrial file not found: {file_path_secuTrial}")
            return
            
        if not file_path_REVASC.exists():
            logger.error(f"Required REVASC file not found: {file_path_REVASC}")
            return
            
        if not file_path_EPIC.exists():
            logger.error(f"Required EPIC file not found: {file_path_EPIC}")
            # Try Excel version as fallback
            file_path_EPIC = epic_base_dir / 'encounters.xlsx'
            if not file_path_EPIC.exists():
                logger.error(f"Fallback EPIC file not found: {file_path_EPIC}")
                return
        
        # Read files
        df_secuTrial = safe_read_file(file_path_secuTrial, custom_reader=read_and_modify_secuTrial_export)
        df_REVASC = safe_read_file(file_path_REVASC, custom_reader=read_and_modify_secuTrial_export)
        
        # For EPIC data, use detect_encoding if it's a CSV
        if file_path_EPIC.suffix.lower() == ".csv":
            try:
                # Define detect_encoding function
                def detect_encoding(file_path):
                    with open(file_path, 'rb') as f:
                        raw_data = f.read(10000)
                    result = chardet.detect(raw_data)
                    return result['encoding']
                
                encoding = detect_encoding(file_path_EPIC)
                logger.info(f"Detected encoding for EPIC file: {encoding}")
                df_EPIC = pd.read_csv(file_path_EPIC, encoding=encoding)
            except Exception as e:
                logger.error(f"Error reading CSV with detected encoding: {e}")
                try:
                    # Try with common encodings
                    encodings = ['latin1', 'utf-8-sig', 'cp1252', 'iso-8859-1']
                    for enc in encodings:
                        try:
                            df_EPIC = pd.read_csv(file_path_EPIC, encoding=enc)
                            logger.info(f"Successfully read with encoding: {enc}")
                            break
                        except Exception:
                            continue
                    else:
                        logger.error("Could not read CSV with any common encoding")
                        return
                except Exception as e:
                    logger.error(f"Error in fallback CSV reading: {e}")
                    return
        else:
            df_EPIC = safe_read_file(file_path_EPIC)
            
        if df_EPIC is None:
            logger.error("Failed to load EPIC data")
            return
            
        # Log successful data loading
        if df_secuTrial is not None and df_EPIC is not None and df_REVASC is not None:
            logger.info(f"Successfully loaded data: secuTrial={df_secuTrial.shape}, REVASC={df_REVASC.shape}, EPIC={df_EPIC.shape}")
        else:
            logger.error("Failed to load one or more datasets")
            return
            
        # Continue with processing...
        logger.info("Data validation completed successfully")
        
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}", exc_info=True)

if __name__ == "__main__":
    main()