#!/usr/bin/env python3
"""
EPIC-secuTrial Import Service
Converted from Jupyter notebook to standalone Python script with logging

Original notebook: import_EPIC2sT_20250303.ipynb
Created by: Yasaman Safarkhanlo
"""

import pandas as pd
import os
import numpy as np
from datetime import datetime
from pathlib import Path
import openpyxl
import json
import logging
from typing import Dict, Any, Optional, Tuple, List, Union
import chardet

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    log_dir = Path("/app/data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"import_service_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('epic-import')

logger = setup_logging()

def prefix_map(file_type):
    """Returns the prefix based on the file type for renaming columns."""
    prefix_dict = {
        "encounter": "enct.",
        "flowsheet": "flow.",
        "imaging": "img.",
        "lab": "lab.",
        "medication": "med.",
        "monitor": "mon."
    }
    return prefix_dict.get(file_type, "")

def detect_encoding(file_path):
    """Detect the encoding of a file using chardet."""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    return result['encoding']

def merge_excel_files(directory, merge_column):
    """
    Merges all EPIC files in a directory based on a specific column, in a defined order.

    Parameters:
        directory (str or Path): Directory containing files.
        merge_column (str): Column name to use for merging files.

    Returns:
        pd.DataFrame
    """
    # Define merge order and column prefixes
    merge_order = {
        "encounters": "enct.",
        "flowsheet": "flow.",
        "imaging": "img.",
        "lab": "lab.",
        "medication": "med.",
        "monitor": "mon."
    }

    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory {directory} does not exist.")

    merged_df = pd.DataFrame()

    # Merge files in the defined order
    for keyword, prefix in merge_order.items():
        for file in directory.glob(f"*{keyword}*"):
            if file.suffix.lower() in [".xlsx", ".xls", ".csv"]:  # Check for valid file extensions
                merged_df = merge_single_file(file, merge_column, merged_df, prefix)

    for file in directory.glob("*"):
        if file.suffix.lower() in [".xlsx", ".xls", ".csv"]:  # Ensure only valid file types are processed
            if not any(keyword in file.stem for keyword in merge_order):
                merged_df = merge_single_file(file, merge_column, merged_df)

    return merged_df

def merge_single_file(file_path, merge_column, merged_df, prefix=""):
    """
    Merges a single file into the main DataFrame with optional prefixing of columns.

    Parameters:
        file_path (str or Path): Path to file.
        merge_column (str): Column name to merge on.
        merged_df (pd.DataFrame): The main DataFrame to merge into.
        prefix (str): Optional prefix to add to column names for this file.

    Returns:
        pd.DataFrame: Updated merged DataFrame.
    """
    # Determine file extension
    file_extension = file_path.suffix.lower()

    # Try to detect encoding for CSV files
    detected_encoding = None
    if file_extension == ".csv":
        detected_encoding = detect_encoding(file_path)
        logger.info(f"Detected encoding for {file_path.name}: {detected_encoding}")

    # Read file based on its extension
    try:
        if file_extension == ".xlsx":
            df = pd.read_excel(file_path, engine='openpyxl')
        elif file_extension == ".xls":
            df = pd.read_excel(file_path, engine='xlrd')
        elif file_extension == ".csv":
            # Try with the detected encoding
            try:
                df = pd.read_csv(file_path, encoding=detected_encoding)
            except Exception:
                # If that fails, try common encodings
                encodings_to_try = ['latin1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
                for encoding in encodings_to_try:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        logger.info(f"Successfully read {file_path.name} with encoding: {encoding}")
                        break
                    except Exception as e:
                        logger.info(f"Failed with encoding {encoding}: {e}")
                else:
                    # Last resort: try with different delimiters
                    delimiters = [',', ';', '|', '\t']
                    for delim in delimiters:
                        try:
                            df = pd.read_csv(file_path, encoding='latin1', sep=delim)
                            logger.info(f"Successfully read {file_path.name} with delimiter: '{delim}'")
                            break
                        except Exception as e:
                            logger.info(f"Failed with delimiter '{delim}': {e}")
                    else:
                        raise ValueError(f"Could not read file with any encoding or delimiter")
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return merged_df  # Return the existing DataFrame without merging

    # Check if merge column exists
    if merge_column not in df.columns:
        logger.warning(f"Warning: Merge column '{merge_column}' not found in {file_path.name}")
        logger.warning(f"Available columns: {df.columns.tolist()}")
        return merged_df
        
    # Print number of columns in the current file
    logger.info(f"File: {file_path.name} | Columns: {len(df.columns)} , Rows: {df.shape[0]}")

    # Add prefix to columns except the merge column
    df.rename(columns={col: f"{prefix}{col}" for col in df.columns if col != merge_column}, inplace=True)

    # Merge the DataFrame into the main DataFrame
    if merged_df.empty:
        return df
    else:
        # Check if merge column exists in both DataFrames
        if merge_column in merged_df.columns:
            return merged_df.merge(df, on=merge_column, how="outer")
        else:
            logger.warning(f"Warning: Merge column '{merge_column}' not found in merged DataFrame")
            logger.warning(f"Merged DataFrame columns: {merged_df.columns.tolist()}")
            return merged_df

def read_and_modify_secuTrial_export(df):
    """Process secuTrial export dataframe"""
    logger.info("Processing secuTrial export dataframe")
    try:
        df = df.drop([7])                   # Remove row 8 in Excel
        df = df.iloc[6:]                    # Skip the first 6 rows
        df.columns = df.iloc[0]             # Use row 6 as the header
        df = df[1:].reset_index(drop=True)  # Drop the header row and reset index
        logger.info(f"Successfully processed secuTrial dataframe with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error in read_and_modify_secuTrial_export: {e}")
        return None

def safe_read_file(file_path, custom_reader=None):
    """
    Safely reads a file (Excel or CSV), with an option for a custom reader function.
    
    Parameters:
        file_path (str or Path)
        custom_reader (function, optional)

    Returns:
        pd.DataFrame
    """
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()

    try:
        # Read based on file extension
        if file_extension in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path, engine='openpyxl' if file_extension == ".xlsx" else 'xlrd', header=None)
        elif file_extension == ".csv":
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Apply custom reader if provided
        return custom_reader(df) if custom_reader else df

    except FileNotFoundError:
        logger.error(f"Error: File not found at {file_path}")
    except Exception as e:
        logger.error(f"Error reading file at {file_path}: {e}")
    
    return None

def create_import_file(df_EPIC, dictionary, start_id=13744):
    """Creates a DataFrame for import into secuTrial using values mapped from EPIC data."""
    logger.info(f"Creating import file with start_id={start_id}")

    # Load the mapping file and initialize the import DataFrame
    mapping_df = pd.read_excel(dictionary)
    today_date = datetime.today().date()

    df_import = pd.DataFrame({
        'case_id': [f'SSR-INS-{i}' for i in range(start_id, start_id + len(df_EPIC))],
        'visit_name': ["Acute Phase"] * len(df_EPIC),
        'center_id': ["Bern Inselspital (SSR)"] * len(df_EPIC),
        'entry_date': [today_date] * len(df_EPIC)
    })

    # Map and add columns based on the mapping file
    for _, row in mapping_df.iterrows():
        column_source = row['EPIC_table']
        if pd.isna(column_source): 
            continue

        prefix = ""
        if "Encounters" in column_source: prefix = "enct."
        elif "Flowsheet" in column_source: prefix = "flow."
        elif "Imaging" in column_source: prefix = "img."
        elif "Lab" in column_source: prefix = "lab."
        elif "Medications" in column_source: prefix = "med."

        epic_column = f"{prefix}{row['EPIC_field']}"
        secuTrial_column = f"{row['secuTrial_import_table']}.{row['secuTrial_import_field']}"

        if epic_column in df_EPIC.columns:
            df_import[secuTrial_column] = df_EPIC[epic_column]
        else:
            df_import[secuTrial_column] = ''

    # Process datetime columns
    logger.info("Processing date and time columns")
    # Merge _date and _time columns into a single datetime column where both exist
    for date_col in df_import.columns:
        if date_col.endswith('_date'):
            time_col = date_col.replace('_date', '_time')
            if time_col in df_import.columns:
                # Combine _date and _time columns if both are present
                combined_datetime = df_import[date_col].astype(str) + ' ' + df_import[time_col].astype(str)

                # Parse combined datetime and format it
                df_import[date_col] = pd.to_datetime(combined_datetime, errors='coerce').dt.strftime('%d.%m.%Y %H:%M:%S')

                # Drop original _time column after merging
                df_import.drop(columns=[time_col], inplace=True)
            else:
                # Format _date column alone if no corresponding _time column
                df_import[date_col] = pd.to_datetime(df_import[date_col], errors='coerce').dt.strftime('%d.%m.%Y %H:%M:%S')

    # Check if both `enct.arrival_date` and `enct.arrival_time` exist in df_import
    if 'enct.arrival_date' in df_import.columns and 'enct.arrival_time' in df_import.columns:
        # Combine `enct.arrival_date` and `enct.arrival_time` into a single datetime column
        combined_datetime = df_import['enct.arrival_date'].astype(str) + ' ' + df_import['enct.arrival_time'].astype(str)
    
        # Parse and format the combined datetime column
        df_import['enct.arrival_date'] = pd.to_datetime(combined_datetime, errors='coerce').dt.strftime('%d.%m.%Y %H:%M:%S')
    
        # Drop the original `enct.arrival_time` column after merging
        df_import.drop(columns=['enct.arrival_time'], inplace=True)

    # Format numeric columns
    logger.info("Formatting numeric columns")
    # Round height and weight columns to the nearest integer and cast them to integer if they exist
    for col in ['Acute.height', 'Acute.weight']:
        if col in df_import.columns:
            df_import[col] = np.ceil(df_import[col]).astype('Int64')

    # Remove Acute.zip values if Acute.non_swiss is 1
    if 'Acute.non_swiss' in df_import.columns and 'Acute.zip' in df_import.columns:
        df_import.loc[df_import['Acute.non_swiss'] == 1, 'Acute.zip'] = ''

    # Format integer columns as needed
    for column in df_import.columns:
        if df_import[column].dropna().isin([0, 1, 2, 3, 4]).all():
            df_import[column] = df_import[column].astype('Int64')
        elif pd.api.types.is_numeric_dtype(df_import[column]):
            df_import[column] = df_import[column].round(1)

    logger.info(f"Import file created with shape: {df_import.shape}")
    return df_import

def main():
    """Main function for the import service"""
    logger.info("Starting EPIC-secuTrial Import Service")
    
    # Use environment variable for base directory with fallback
    base_dir = Path(os.environ.get("BASE_DIR", "/app/data"))
    logger.info(f"Using base directory: {base_dir}")
    
    # Check if required directories exist
    required_dirs = [
        base_dir / "EPIC-files",
        base_dir / "sT-files",
        base_dir / "EPIC2sT-pipeline",
        base_dir / "sT-import-validation"
    ]
    
    for directory in required_dirs:
        if not directory.exists():
            logger.warning(f"Required directory does not exist: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    try:
        # Try to find latest export folders
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
        REVASC_base_dir = secuTrial_base_dir / 'REVASC'
        epic_base_dir = latest_EPIC_export
        
        # Merge all EPIC files
        logger.info("Starting to merge EPIC files")
        df_EPIC_all = merge_excel_files(epic_base_dir, merge_column="PAT_ENC_CSN_ID")
        logger.info(f"Merged EPIC data with shape: {df_EPIC_all.shape}")
        
        # Read ID log file
        id_log_path = base_dir / 'EPIC2sT-pipeline/Identification_log_SSR_2024_ohne PW_26.03.25.xlsx'
        
        if not id_log_path.exists():
            logger.error(f"ID log file not found: {id_log_path}")
            return
            
        id_log = pd.read_excel(id_log_path)
        
        # Set the first row as column names and drop it from the data
        id_log.columns = id_log.iloc[0]
        id_log = id_log.iloc[1:].reset_index(drop=True)  # Reset index for clarity
        
        # Rename columns for consistency
        id_log.rename(columns={'Fall-Nr.': 'FID', 'SSR Identification SSR-INS-000....': 'SSR'}, inplace=True)
        logger.info(f"Loaded ID log with {len(id_log)} entries")
        
        # Extract FID from img.FID if available
        if 'img.FID' in df_EPIC_all.columns:
            df_EPIC_all['FID'] = df_EPIC_all['img.FID'].fillna(0).astype(int)
            df_EPIC_all.insert(0, 'FID', df_EPIC_all.pop('FID'))
            
        # Merge with df_EPIC_all on 'FID' and reorder columns
        df_EPIC_all = df_EPIC_all.merge(id_log[['FID', 'SSR']], on='FID', how='left')
        df_EPIC_all.insert(1, 'SSR', df_EPIC_all.pop('SSR'))  # Move 'SSR' to the second column
        
        # Define mapping file path
        mapping_file = base_dir / 'sT-import-validation/map_epic2secuTrial_import.xlsx'
        
        if not mapping_file.exists():
            logger.error(f"Mapping file not found: {mapping_file}")
            return
        
        # Create import file
        logger.info("Creating import file from EPIC data")
        start_id = 13744  # Default starting ID for SSR cases
        import_file_df = create_import_file(df_EPIC_all, mapping_file, start_id=start_id)
        
        # Generate timestamp for output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save the import file
        output_dir = base_dir / 'EPIC2sT-pipeline'
        output_file = output_dir / f"SSR-INS-2024_import_{timestamp}.csv"
        
        # Filter out REVASC columns for final import file
        import_file_df_filtered = import_file_df.loc[:, ~import_file_df.columns.str.startswith('REVASC')]
        
        # Save to CSV with semicolon delimiter (common format for secuTrial imports)
        import_file_df.to_csv(output_dir / f"SSR-INS-2024_import_with_REVASC_{timestamp}.csv", index=False, sep=';')
        import_file_df_filtered.to_csv(output_file, index=False, sep=';')
        
        logger.info(f"Import files saved to {output_dir}")
        logger.info(f"Main import file: {output_file}")
        logger.info(f"File shape: {import_file_df_filtered.shape}")
        
        # Save a copy of the merged EPIC data for reference
        df_EPIC_all.to_excel(output_dir / f"merged_EPIC_data_{timestamp}.xlsx", index=False)
        
        logger.info("Import process completed successfully")
        
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}", exc_info=True)

if __name__ == "__main__":
    main()
        