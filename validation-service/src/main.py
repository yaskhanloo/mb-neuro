#!/usr/bin/env python3
"""
EPIC-secuTrial Validation Service
Enhanced with complete comparison logic from notebook

Original notebook: validation_EPIC2secuTrial_V4_20250227.ipynb
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

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    log_dir = Path("/app/data/logs")
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

logger = setup_logging()

# Read files
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
            df = pd.read_excel(file_path, engine='openpyxl' if file_extension == ".xlsx" else 'xlrd')
        elif file_extension == ".csv":
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                raise ValueError("Could not read CSV with any encoding")
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        result = custom_reader(df) if custom_reader else df

        if result is None or result.empty:
            logger.warning(f"{file_path.name} is empty after processing.")
            return None

        logger.info(f"Successfully read file: {file_path.name}")
        return result

    except FileNotFoundError:
        logger.error(f"File not found at {file_path}")
    except Exception as e:
        logger.error(f"Error reading file at {file_path}: {e}")
    
    return None

# EPIC merge
def merge_single_file(file_path, merge_column, merged_df, prefix=""):
    """
    Merge a single file into the main DataFrame with optional column prefixing.
    """
    # Read file
    df = safe_read_file(file_path)
    if df is None or merge_column not in df.columns:
        logger.warning(f"Skipping {file_path.name}: file read failed or merge column '{merge_column}' not found")
        return merged_df
    
    # Add prefix and merge
    if prefix:
        df = df.rename(columns={col: f"{prefix}{col}" for col in df.columns if col != merge_column})
    
    return df if merged_df.empty else merged_df.merge(df, on=merge_column, how="outer")

def merge_excel_files(directory, merge_column):
    """
    Merges all EPIC files in a directory based on a specific column, in a defined order.
    """
    directory = Path(directory)
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory {directory} does not exist.")
    
    # Get prefix for filename
    def get_prefix(filename):
        name = filename.lower()
        prefixes = {
            'enc': 'enct.', 
            'flow': 'flow.', 
            'imag': 'img.', 
            'img': 'img.',
            'lab': 'lab.', 
            'med': 'med.', 
            'mon': 'mon.'
        }
        return next((prefix for key, prefix in prefixes.items() if key in name), "")
    
    # Find all supported files (FIXED: proper glob patterns)
    supported_extensions = ['.xlsx', '.xls', '.csv']
    all_files = [f for f in directory.iterdir() 
                 if f.is_file() and f.suffix.lower() in supported_extensions]
    
    logger.info(f"Found {len(all_files)} files to merge: {[f.name for f in all_files]}")
    
    # Merge all files
    merged_df = pd.DataFrame()
    for file_path in all_files:
        prefix = get_prefix(file_path.stem)
        merged_df = merge_single_file(file_path, merge_column, merged_df, prefix)
        logger.info(f"Merged {file_path.name} -> {prefix or 'no prefix'} (shape: {merged_df.shape})")
    
    return merged_df

# Comparison function
def compare_epic_secuTrial(epic_df, secuTrial_df, mapping_df, value_mappings=None):
    """
    Compares values and data types between EPIC and secuTrial DataFrames using a mapping file,
    accounting for data type differences properly. Includes monthly breakdown of statistics
    and variable-level statistics.
    
    Args:
        epic_df (DataFrame): The EPIC dataset.
        secuTrial_df (DataFrame): The SecuTrial dataset.
        mapping_df (DataFrame): The mapping Excel file with data type information.
        value_mappings (dict, optional): Dictionary for value conversions in EPIC.
        
    Returns:
        DataFrame: DataFrame with mismatched results in values and data types.
        dict: Dictionary containing percentage statistics.
        dict: Dictionary containing monthly statistics.
        dict: Dictionary containing variable-level statistics.
    """
    
    if value_mappings is None:
        value_mappings = {}
        
    # Create working copies to avoid modifying original dataframes
    epic_df_copy = epic_df.copy()
    secuTrial_df_copy = secuTrial_df.copy()
    
    # Replace missing value indicators
    epic_df_copy.replace(-9999, pd.NA, inplace=True)
    secuTrial_df_copy.replace(-9999, pd.NA, inplace=True)

    # Ensure necessary columns exist before comparison
    if "FID" not in epic_df_copy.columns or "SSR" not in epic_df_copy.columns:
        logger.error("EPIC DataFrame must contain 'FID' and 'SSR' columns.")
        raise ValueError("EPIC DataFrame must contain 'FID' and 'SSR' columns.")
    if "FID" not in secuTrial_df_copy.columns or "SSR" not in secuTrial_df_copy.columns:
        logger.error("SecuTrial DataFrame must contain 'FID' and 'SSR' columns.")
        raise ValueError("SecuTrial DataFrame must contain 'FID' and 'SSR' columns.")
        
    # Check for date columns
    if "enct.arrival_date" not in epic_df_copy.columns:
        logger.error("EPIC DataFrame must contain 'enct.arrival_date' column for monthly breakdown.")
        raise ValueError("EPIC DataFrame must contain 'enct.arrival_date' column for monthly breakdown.")
    if "Arrival at hospital" not in secuTrial_df_copy.columns:
        logger.error("SecuTrial DataFrame must contain 'Arrival at hospital' column for monthly breakdown.")
        raise ValueError("SecuTrial DataFrame must contain 'Arrival at hospital' column for monthly breakdown.")

    # Convert date columns
    epic_df_copy['DATE'] = pd.to_datetime(epic_df_copy['enct.arrival_date'], errors='coerce')
    secuTrial_df_copy['DATE'] = pd.to_datetime(secuTrial_df_copy['Arrival at hospital'], errors='coerce')

    # Create a set of (FID, SSR) pairs that exist in both DataFrames
    matching_keys = set(epic_df_copy[['FID', 'SSR']].apply(tuple, axis=1)) & set(secuTrial_df_copy[['FID', 'SSR']].apply(tuple, axis=1))
    logger.info(f"Found {len(matching_keys)} matching (FID, SSR) pairs for comparison")

    # Store mismatched results
    mismatched_results = []
    match_count = 0
    secu_missing_count = 0
    epic_missing_count = 0
    mismatch_count = 0
    total_comparisons = 0
    
    # Setup monthly statistics tracking
    months = {4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 
              9: 'September', 10: 'October', 11: 'November', 12: 'December'}
    
    monthly_stats = {month_name: {'match_count': 0, 'secu_missing_count': 0, 
                                'epic_missing_count': 0, 'mismatch_count': 0, 
                                'total_compared': 0} 
                   for month_name in months.values()}
    
    # Create a dictionary to store variable-level statistics
    variable_stats = {}
    
    # Helper function to standardize boolean values
    def standardize_boolean(value):
        if pd.isna(value):
            return pd.NA
        
        if isinstance(value, bool):
            return "yes" if value else "no"
        elif isinstance(value, (int, float)):
            return "yes" if value else "no"
        elif isinstance(value, str):
            if value.lower() in ['true', 'yes', 'y', '1', 't']:
                return "yes"
            elif value.lower() in ['false', 'no', 'n', '0', 'f']:
                return "no"
        
        return str(value)
    
    # Helper function to convert values to the correct type
    def convert_to_type(value, target_type):
        """Convert value to specified type with specific formatting"""
        if pd.isna(value):
            return pd.NA
            
        # Handle various data types
        if not isinstance(target_type, str):
            return value  # If no type specified, return as is
            
        # Check for float with decimal specification (e.g., float-1, float-2)
        float_match = re.match(r'float-(\d+)', target_type.lower())
        if float_match:
            try:
                decimal_places = int(float_match.group(1))
                if value == '':
                    return pd.NA
                float_val = float(value)
                return round(float_val, decimal_places)
            except (ValueError, TypeError):
                return pd.NA
        
        if target_type.lower() in ['int', 'integer', 'int64', 'int32']:
            try:
                return int(float(value)) if value != '' else pd.NA
            except (ValueError, TypeError):
                return pd.NA
        elif target_type.lower() in ['float', 'double', 'numeric', 'float64', 'float32']:
            try:
                return float(value) if value != '' else pd.NA
            except (ValueError, TypeError):
                return pd.NA
        elif target_type.lower() in ['date', 'datetime', 'timestamp']:
            try:
                if value == '':
                    return pd.NA
                # Convert to datetime and then to yyyymmdd hh:mm format
                dt = pd.to_datetime(value)
                return dt.strftime('%Y%m%d %H:%M')
            except (ValueError, TypeError, AttributeError):
                return pd.NA
        elif target_type.lower() in ['bool', 'boolean']:
            return standardize_boolean(value)
        else:
            # Default to string for text, categorical, etc.
            return str(value) if value is not None and value != '' else pd.NA
    
    # Helper function to check if values are equivalent
    def equivalent_values(val1, val2, target_type):
        """Compare values with formatted type awareness"""
        # Handle NaN values consistently
        if pd.isna(val1) and pd.isna(val2):
            return True
        elif pd.isna(val1) or pd.isna(val2):
            return False
            
        # Check for float with decimal specification (e.g., float-1, float-2)
        float_match = re.match(r'float-(\d+)', target_type.lower()) if isinstance(target_type, str) else None
        if float_match:
            try:
                decimal_places = int(float_match.group(1))
                val1_rounded = round(float(val1), decimal_places)
                val2_rounded = round(float(val2), decimal_places)
                return val1_rounded == val2_rounded
            except (ValueError, TypeError):
                return False
        
        # Boolean comparison (standardized to yes/no)
        if isinstance(target_type, str) and target_type.lower() in ['bool', 'boolean']:
            val1_std = standardize_boolean(val1)
            val2_std = standardize_boolean(val2)
            return val1_std == val2_std
        
        # Special handling for numeric types
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            try:
                return abs(float(val1) - float(val2)) < 1e-6
            except (ValueError, TypeError):
                return False
        
        # Date comparison (already in string format)
        if isinstance(target_type, str) and target_type.lower() in ['date', 'datetime', 'timestamp']:
            return val1 == val2
            
        # String comparison (case insensitive)
        elif isinstance(val1, str) and isinstance(val2, str):
            return val1.strip().lower() == val2.strip().lower()
            
        # Default comparison
        else:
            return str(val1) == str(val2)
    
    # Build a column mapping dictionary for easier lookups
    column_mappings = {}
    column_types = {}
    
    for _, row in mapping_df.iterrows():
        epic_column_name = row.get('EPIC_varColumnName', None)
        secuTrial_column_name = row.get('sT_varColumnName', None)
        epic_dtype = row.get('EPIC_varType', 'text')  # Default to text if not specified
        secuTrial_dtype = row.get('sT_varType', 'text')  # Default to text if not specified
        column_source = row.get('EPIC_exportFileName', None)
        secu_source = row.get('sT_exportFileName', None)

        if not isinstance(epic_column_name, str) or not isinstance(secuTrial_column_name, str):
            continue  # Skip if column names are missing

        # Determine EPIC column prefix
        prefix = ""
        if isinstance(column_source, str):
            if "encounter" in column_source.lower():
                prefix = "enct."
            elif "flowsheet" in column_source.lower():
                prefix = "flow."
            elif "imaging" in column_source.lower():
                prefix = "img."
            elif "lab" in column_source.lower():
                prefix = "lab."
            elif "medication" in column_source.lower():
                prefix = "med."
            elif "monitor" in column_source.lower():
                prefix = "mon."

        # Determine SecuTrial column suffix
        suffix = ""
        if isinstance(secu_source, str) and "REVASC" in secu_source:
            suffix = ".revas"

        # Construct fully qualified column names
        epic_col = f"{prefix}{epic_column_name}"  # EPIC column with prefix
        secu_col = f"{secuTrial_column_name}{suffix}"  # SecuTrial column with suffix
        
        # If secuTrial type is int, override EPIC type to also be int
        if secuTrial_dtype.lower() in ['int', 'integer', 'int64', 'int32']:
            epic_dtype = 'int'
        # If secuTrial type is float or float-n, override EPIC type
        elif secuTrial_dtype.lower() in ['float', 'double', 'numeric', 'float64', 'float32'] or re.match(r'float-\d+', secuTrial_dtype.lower()):
            epic_dtype = secuTrial_dtype
        
        # Store the mapping
        column_mappings[epic_col] = secu_col
        column_types[epic_col] = {'epic_type': epic_dtype, 'secu_type': secuTrial_dtype}
        
        # Initialize variable stats for this column pair
        variable_stats[f"{epic_col} <-> {secu_col}"] = {
            'match_count': 0,
            'epic_missing_count': 0,
            'secu_missing_count': 0,
            'mismatch_count': 0,
            'total_compared': 0,
            'epic_type': epic_dtype,
            'secu_type': secuTrial_dtype
        }
    
    # First, apply value mappings to EPIC data
    for col, mapping in value_mappings.items():
        if col in epic_df_copy.columns:
            epic_df_copy[col] = epic_df_copy[col].map(lambda x: mapping.get(x, x))
    
    # Next, convert data types in both dataframes
    for epic_col, secu_col in column_mappings.items():
        # For EPIC dataframe
        if epic_col in epic_df_copy.columns:
            target_type = column_types[epic_col]['epic_type']
            epic_df_copy[epic_col] = epic_df_copy[epic_col].apply(lambda x: convert_to_type(x, target_type))
        
        # For secuTrial dataframe
        if secu_col in secuTrial_df_copy.columns:
            target_type = column_types[epic_col]['secu_type']
            secuTrial_df_copy[secu_col] = secuTrial_df_copy[secu_col].apply(lambda x: convert_to_type(x, target_type))
    
    # Now compare the values
    logger.info("Beginning comparison between EPIC and secuTrial data")
    for epic_col, secu_col in column_mappings.items():
        var_key = f"{epic_col} <-> {secu_col}"
        
        # Check if columns exist in respective DataFrames
        if epic_col not in epic_df_copy.columns and secu_col in secuTrial_df_copy.columns:
            epic_missing_count += 1
            variable_stats[var_key]['epic_missing_count'] += 1
            variable_stats[var_key]['total_compared'] += 1
            continue
        elif secu_col not in secuTrial_df_copy.columns and epic_col in epic_df_copy.columns:
            secu_missing_count += 1
            variable_stats[var_key]['secu_missing_count'] += 1
            variable_stats[var_key]['total_compared'] += 1
            continue
        elif epic_col not in epic_df_copy.columns and secu_col not in secuTrial_df_copy.columns:
            continue  # Skip comparison if column is missing in both

        total_comparisons += 1
        
        # Get target type for this column
        target_type = column_types[epic_col]['secu_type']  # Use secuTrial type as the target

        # Compare values for rows with matching (FID, SSR)
        for fid, ssr in matching_keys:
            epic_row = epic_df_copy.loc[(epic_df_copy["FID"] == fid) & (epic_df_copy["SSR"] == ssr)]
            secu_row = secuTrial_df_copy.loc[(secuTrial_df_copy["FID"] == fid) & (secuTrial_df_copy["SSR"] == ssr)]
            
            if epic_row.empty or secu_row.empty:
                continue  # Skip if no matching row found
                
            epic_value = epic_row[epic_col].iloc[0] if epic_col in epic_row.columns else pd.NA
            secu_value = secu_row[secu_col].iloc[0] if secu_col in secu_row.columns else pd.NA
            
            # Get the month for this record (use epic date if available, else secu date)
            record_date = None
            if not epic_row.empty and 'DATE' in epic_row.columns and not pd.isna(epic_row['DATE'].iloc[0]):
                record_date = epic_row['DATE'].iloc[0]
            elif not secu_row.empty and 'DATE' in secu_row.columns and not pd.isna(secu_row['DATE'].iloc[0]):
                record_date = secu_row['DATE'].iloc[0]
                
            # Skip if no valid date or not in April-December range
            if record_date is None:
                continue
                
            record_month = record_date.month
            # Skip if not in our target month range (April-December)
            if record_month < 4 or record_month > 12:
                continue
                
            month_name = months[record_month]
                
            # Both values are NaN/missing - count as match
            if pd.isna(epic_value) and pd.isna(secu_value):
                match_count += 1
                monthly_stats[month_name]['match_count'] += 1
                monthly_stats[month_name]['total_compared'] += 1
                variable_stats[var_key]['match_count'] += 1
                variable_stats[var_key]['total_compared'] += 1
                continue
                
            # Only secuTrial value is NaN/missing
            if pd.isna(secu_value) and not pd.isna(epic_value):
                secu_missing_count += 1
                monthly_stats[month_name]['secu_missing_count'] += 1
                monthly_stats[month_name]['total_compared'] += 1
                variable_stats[var_key]['secu_missing_count'] += 1
                variable_stats[var_key]['total_compared'] += 1
                continue
                
            # Only EPIC value is NaN/missing
            if pd.isna(epic_value) and not pd.isna(secu_value):
                epic_missing_count += 1
                monthly_stats[month_name]['epic_missing_count'] += 1
                monthly_stats[month_name]['total_compared'] += 1
                variable_stats[var_key]['epic_missing_count'] += 1
                variable_stats[var_key]['total_compared'] += 1
                continue

            # Compare values using the target type
            if equivalent_values(epic_value, secu_value, target_type):
                match_count += 1
                monthly_stats[month_name]['match_count'] += 1
                variable_stats[var_key]['match_count'] += 1
            else:
                mismatch_count += 1
                monthly_stats[month_name]['mismatch_count'] += 1
                variable_stats[var_key]['mismatch_count'] += 1
                mismatched_results.append({
                    'FID': fid,
                    'SSR': ssr,
                    'Month': month_name,
                    'DATE': record_date,
                    'EPIC Column': epic_col,
                    'SecuTrial Column': secu_col,
                    'EPIC Value': str(epic_value),
                    'SecuTrial Value': str(secu_value),
                    'EPIC Expected Type': column_types[epic_col]['epic_type'],
                    'SecuTrial Expected Type': target_type,
                    'EPIC Actual Type': type(epic_value).__name__,
                    'SecuTrial Actual Type': type(secu_value).__name__
                })
            
            monthly_stats[month_name]['total_compared'] += 1
            variable_stats[var_key]['total_compared'] += 1

    # Calculate percentages
    total_compared = match_count + mismatch_count + secu_missing_count + epic_missing_count
    percentage_stats = {
        "Matching Variables (%)": round((match_count / total_compared) * 100, 2) if total_compared else 0,
        "Variables Missing in EPIC (%)": round((epic_missing_count / total_compared) * 100, 2) if total_compared else 0,
        "Variables Missing in SecuTrial (%)": round((secu_missing_count / total_compared) * 100, 2) if total_compared else 0,
        "Mismatched Variables (%)": round((mismatch_count / total_compared) * 100, 2) if total_compared else 0,
        "Total Comparisons": total_compared,
        "Matches": match_count,
        "EPIC Missing": epic_missing_count,
        "SecuTrial Missing": secu_missing_count,
        "Mismatches": mismatch_count
    }
    
    # Calculate monthly percentages
    monthly_percentage_stats = {}
    for month, stats in monthly_stats.items():
        total = stats['total_compared']
        if total > 0:
            monthly_percentage_stats[month] = {
                "Matching Variables (%)": round((stats['match_count'] / total) * 100, 2),
                "Variables Missing in EPIC (%)": round((stats['epic_missing_count'] / total) * 100, 2),
                "Variables Missing in SecuTrial (%)": round((stats['secu_missing_count'] / total) * 100, 2),
                "Mismatched Variables (%)": round((stats['mismatch_count'] / total) * 100, 2),
                "Total Comparisons": total,
                "Matches": stats['match_count'],
                "EPIC Missing": stats['epic_missing_count'],
                "SecuTrial Missing": stats['secu_missing_count'],
                "Mismatches": stats['mismatch_count']
            }
        else:
            monthly_percentage_stats[month] = {
                "Matching Variables (%)": 0,
                "Variables Missing in EPIC (%)": 0,
                "Variables Missing in SecuTrial (%)": 0,
                "Mismatched Variables (%)": 0,
                "Total Comparisons": 0,
                "Matches": 0,
                "EPIC Missing": 0,
                "SecuTrial Missing": 0,
                "Mismatches": 0
            }
    
    # Calculate variable-level percentages
    variable_percentage_stats = {}
    for var_key, stats in variable_stats.items():
        total = stats['total_compared']
        if total > 0:
            variable_percentage_stats[var_key] = {
                "Matching Values (%)": round((stats['match_count'] / total) * 100, 2),
                "Values Missing in EPIC (%)": round((stats['epic_missing_count'] / total) * 100, 2),
                "Values Missing in SecuTrial (%)": round((stats['secu_missing_count'] / total) * 100, 2),
                "Mismatched Values (%)": round((stats['mismatch_count'] / total) * 100, 2),
                "Total Comparisons": total,
                "Matches": stats['match_count'],
                "EPIC Missing": stats['epic_missing_count'],
                "SecuTrial Missing": stats['secu_missing_count'],
                "Mismatches": stats['mismatch_count'],
                "EPIC Type": stats['epic_type'],
                "SecuTrial Type": stats['secu_type']
            }
        else:
            variable_percentage_stats[var_key] = {
                "Matching Values (%)": 0,
                "Values Missing in EPIC (%)": 0,
                "Values Missing in SecuTrial (%)": 0,
                "Mismatched Values (%)": 0,
                "Total Comparisons": 0,
                "Matches": 0,
                "EPIC Missing": 0,
                "SecuTrial Missing": 0,
                "Mismatches": 0,
                "EPIC Type": stats['epic_type'],
                "SecuTrial Type": stats['secu_type']
            }
    
    logger.info(f"Comparison complete. Stats: Matches: {match_count}, EPIC Missing: {epic_missing_count}, SecuTrial Missing: {secu_missing_count}, Mismatches: {mismatch_count}")
    return pd.DataFrame(mismatched_results), percentage_stats, monthly_percentage_stats, variable_percentage_stats

def get_top_problematic_variables(variable_stats, sort_by='mismatch_percent', top_n=10):
    """
    Identify the most problematic variables based on specified criteria
    
    Args:
        variable_stats (dict): Dictionary containing variable-level statistics
        sort_by (str): Criteria to sort by: 'mismatch_percent', 'missing_epic_percent', 
                       'missing_secuTrial_percent', or 'total_problems'
        top_n (int): Number of variables to return
        
    Returns:
        DataFrame: Top problematic variables sorted by the specified criteria
    """
    
    # Create a DataFrame from the variable stats
    var_df = pd.DataFrame()
    
    for var_name, stats in variable_stats.items():
        if stats['Total Comparisons'] > 0:  # Only include variables with actual comparisons
            row = {
                'Variable': var_name,
                'Total Comparisons': stats['Total Comparisons'],
                'Match Count': stats['Matches'],
                'Match Percent': stats['Matching Values (%)'],
                'Mismatch Count': stats['Mismatches'],
                'Mismatch Percent': stats['Mismatched Values (%)'],
                'EPIC Missing Count': stats['EPIC Missing'],
                'EPIC Missing Percent': stats['Values Missing in EPIC (%)'],
                'SecuTrial Missing Count': stats['SecuTrial Missing'],
                'SecuTrial Missing Percent': stats['Values Missing in SecuTrial (%)'],
                'EPIC Type': stats['EPIC Type'],
                'SecuTrial Type': stats['SecuTrial Type'],
                'Total Problems': stats['Mismatches'] + stats['EPIC Missing'] + stats['SecuTrial Missing'],
                'Total Problem Percent': (100 - stats['Matching Values (%)'])
            }
            var_df = pd.concat([var_df, pd.DataFrame([row])], ignore_index=True)
    
    # Sort based on criteria
    if sort_by == 'mismatch_percent':
        var_df = var_df.sort_values(by='Mismatch Percent', ascending=False)
    elif sort_by == 'missing_epic_percent':
        var_df = var_df.sort_values(by='EPIC Missing Percent', ascending=False)
    elif sort_by == 'missing_secuTrial_percent':
        var_df = var_df.sort_values(by='SecuTrial Missing Percent', ascending=False)
    elif sort_by == 'total_problems':
        var_df = var_df.sort_values(by='Total Problem Percent', ascending=False)
    else:
        var_df = var_df.sort_values(by='Total Problem Percent', ascending=False)
    
    return var_df.head(top_n)

def generate_comparison_report(mismatched_results, overall_stats, monthly_stats, variable_stats):
    """
    Generates a comprehensive report from the comparison results
    
    Args:
        mismatched_results (DataFrame): DataFrame with details of mismatched values
        overall_stats (dict): Dictionary with overall statistics
        monthly_stats (dict): Dictionary with monthly breakdown of statistics
        variable_stats (dict): Dictionary with variable-level statistics
        
    Returns:
        str: Markdown formatted report
    """
    
    report = io.StringIO()
    
    # Overall Summary
    report.write("# EPIC-SecuTrial Data Comparison Summary\n\n")
    report.write("## Overall Statistics\n\n")
    report.write(f"* Total Comparisons: {overall_stats['Total Comparisons']}\n")
    report.write(f"* Matching Variables: {overall_stats['Matches']} ({overall_stats['Matching Variables (%)']}%)\n")
    report.write(f"* Mismatched Variables: {overall_stats['Mismatches']} ({overall_stats['Mismatched Variables (%)']}%)\n")
    report.write(f"* Variables Missing in EPIC: {overall_stats['EPIC Missing']} ({overall_stats['Variables Missing in EPIC (%)']}%)\n")
    report.write(f"* Variables Missing in SecuTrial: {overall_stats['SecuTrial Missing']} ({overall_stats['Variables Missing in SecuTrial (%)']}%)\n\n")
    
    # Monthly Breakdown
    report.write("## Monthly Statistics\n\n")
    monthly_df = pd.DataFrame(columns=['Month', 'Total Comparisons', 'Matching (%)', 'Mismatched (%)', 
                                     'EPIC Missing (%)', 'SecuTrial Missing (%)'])
    
    for month, stats in monthly_stats.items():
        monthly_df = pd.concat([monthly_df, pd.DataFrame([{
            'Month': month,
            'Total Comparisons': stats['Total Comparisons'],
            'Matching (%)': stats['Matching Variables (%)'],
            'Mismatched (%)': stats['Mismatched Variables (%)'],
            'EPIC Missing (%)': stats['Variables Missing in EPIC (%)'],
            'SecuTrial Missing (%)': stats['Variables Missing in SecuTrial (%)']
        }])], ignore_index=True)
    
    report.write(monthly_df.to_markdown(index=False))
    report.write("\n\n")
    
    # Top Problematic Variables
    report.write("## Top 10 Problematic Variables\n\n")
    top_vars = get_top_problematic_variables(variable_stats, sort_by='total_problems', top_n=10)
    report.write(top_vars[['Variable', 'Total Comparisons', 'Match Percent', 'Mismatch Percent', 
                         'EPIC Missing Percent', 'SecuTrial Missing Percent', 'EPIC Type', 'SecuTrial Type']]
              .to_markdown(index=False))
    report.write("\n\n")
    
    # Variables with Type Mismatches
    report.write("## Variables with Type Mismatches\n\n")
    type_mismatches = []
    for var_name, stats in variable_stats.items():
        if stats['EPIC Type'] != stats['SecuTrial Type']:
            type_mismatches.append({
                'Variable': var_name,
                'EPIC Type': stats['EPIC Type'],
                'SecuTrial Type': stats['SecuTrial Type'],
                'Mismatch Percent': stats['Mismatched Values (%)']
            })
    
    if type_mismatches:
        type_mismatch_df = pd.DataFrame(type_mismatches)
        report.write(type_mismatch_df.sort_values(by='Mismatch Percent', ascending=False).to_markdown(index=False))
    else:
        report.write("No type mismatches found.\n")
    
    return report.getvalue()

def restructure_mismatched_data(differences_df, epic_df):
    """
    Restructures the mismatched data so that each row represents a single (FID, SSR),
    and each discrepancy appears in separate columns.

    Args:
        differences_df (DataFrame): DataFrame containing mismatched values.
        epic_df (DataFrame): The original EPIC DataFrame to determine column order.

    Returns:
        DataFrame: A structured DataFrame where mismatches are arranged in a single row per patient.
    """
    # Standardize column names to prevent mismatches
    differences_df.rename(columns=lambda x: x.strip(), inplace=True)

    required_columns = ["FID", "SSR", "EPIC Column", "SecuTrial Column", "EPIC Value", "SecuTrial Value"]
    missing_columns = [col for col in required_columns if col not in differences_df.columns]

    if missing_columns:
        logger.error(f"Missing required columns in differences_df: {missing_columns}")
        raise ValueError(f"Missing required columns in differences_df: {missing_columns}")

    # Resolve duplicates by taking the first occurrence
    duplicate_check = differences_df.duplicated(subset=["FID", "SSR", "EPIC Column"], keep=False)
    if duplicate_check.any():
        logger.warning(f"Warning: {duplicate_check.sum()} duplicate rows found. Resolving by taking the first occurrence.")

    differences_df = differences_df.groupby(["FID", "SSR", "EPIC Column"], as_index=False).first()

    # Pivot the table to make each discrepancy a separate column
    pivoted_df = differences_df.pivot(index=["FID", "SSR"], 
                                    columns="EPIC Column", 
                                    values=["SecuTrial Value", "EPIC Value"])

    # Flatten multi-level column names
    pivoted_df.columns = [f"{col[1]}_st" if col[0] == "SecuTrial Value" else f"{col[1]}_ep" 
                        for col in pivoted_df.columns]

    # Reset index to include FID and SSR as columns
    pivoted_df.reset_index(inplace=True)

    # Ensure column order follows the order in the original EPIC DataFrame
    column_order = ["FID", "SSR"]

    # Extract base column names from epic_df (without prefix/suffix)
    base_columns = [col for col in epic_df.columns if not col.startswith(("FID", "SSR"))]

    # Ensure `_st` (SecuTrial) columns appear first, then `_ep` (EPIC) columns
    for col in base_columns:
        if f"{col}_st" in pivoted_df.columns:
            column_order.append(f"{col}_st")
        if f"{col}_ep" in pivoted_df.columns:
            column_order.append(f"{col}_ep")

    # Check if any expected columns are missing
    missing_expected_columns = [col for col in column_order if col not in pivoted_df.columns]
    if missing_expected_columns:
        logger.warning(f"Warning: Some expected columns are missing after pivot: {missing_expected_columns}")

    # Select only available columns and reorder
    column_order = [col for col in column_order if col in pivoted_df.columns]
    pivoted_df = pivoted_df[column_order]

    # Fill NaN values with an empty string for better readability
    pivoted_df.fillna("", inplace=True)

    return pivoted_df

def main():
    """Main function for the validation service"""
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
        
        df_EPIC = safe_read_file(file_path_EPIC)
            
        if df_EPIC is None:
            logger.error("Failed to load EPIC data")
            return
            
        # Check if dataframes are loaded
        if df_secuTrial is None or df_REVASC is None:
            logger.error("Failed to load secuTrial or REVASC data")
            return
            
        # Log successful data loading
        logger.info(f"Successfully loaded data: secuTrial={df_secuTrial.shape}, REVASC={df_REVASC.shape}, EPIC={df_EPIC.shape}")
        
        # Unnamed columns check
        unnamed_columns_secuTrial = [col for col in df_secuTrial.columns if not isinstance(col, str) or not col or col.startswith('Unnamed')]
        if unnamed_columns_secuTrial:
            logger.info(f'Unnamed columns in df_secuTrial: {unnamed_columns_secuTrial}')
        
        unnamed_columns_REVASC = [col for col in df_REVASC.columns if not isinstance(col, str) or not col or col.startswith('Unnamed')]
        if unnamed_columns_REVASC:
            logger.info(f'Unnamed columns in df_REVASC: {unnamed_columns_REVASC}')
        
        # Merge df_REVASC into df_secuTrial based on Case ID
        df_secuTrial_w_REVAS = df_secuTrial.merge(
            df_REVASC,
            how='left',
            left_on='Case ID',
            right_on='CaseID',
            suffixes=('', '.revas')
        )
        
        df_secuTrial_w_REVAS.drop(columns=['CaseID'], inplace=True, errors='ignore')
        df_secuTrial_w_REVAS.reset_index(drop=True, inplace=True)
        
        logger.info(f'df_secuTrial_w_REVAS size: {df_secuTrial_w_REVAS.shape}')
        
        # Extract SSR from Case ID
        df_secuTrial_w_REVAS['SSR'] = df_secuTrial_w_REVAS['Case ID'].str.extract(r'(\d+)$').astype(int)
        df_secuTrial_w_REVAS.insert(1, 'SSR', df_secuTrial_w_REVAS.pop('SSR'))
        df_secuTrial_w_REVAS = df_secuTrial_w_REVAS.drop(columns=['nan'], errors='ignore')
        
        # Read ID log file and merge with data
        id_log = pd.read_excel(base_dir / 'EPIC2sT-pipeline/Identification_log_SSR_2024_ohne PW_26.03.25.xlsx')
        
        # Set the first row as column names and drop it from the data
        id_log.columns = id_log.iloc[0]
        id_log = id_log.iloc[1:].reset_index(drop=True)
        
        # Rename columns for consistency
        id_log.rename(columns={'Fall-Nr.(FID)': 'FID', 'SSR Identification SSR-INS-000....': 'SSR'}, inplace=True)
        
        # Add FID to EPIC dataset if not already there
        if 'FID' not in df_EPIC_all.columns:
            logger.info("Extracting FID from img.FID column in EPIC data")
            df_EPIC_all['FID'] = df_EPIC_all['img.FID'].fillna(0).astype(int)
            df_EPIC_all.insert(0, 'FID', df_EPIC_all.pop('FID'))
        
        # Merge with df_EPIC_all on 'FID' and reorder columns
        df_EPIC_all = df_EPIC_all.merge(id_log[['FID', 'SSR']], on='FID', how='left')
        df_EPIC_all.insert(1, 'SSR', df_EPIC_all.pop('SSR'))  # Move 'SSR' to the second column
        
        # Merge with df_secuTrial_w_REVAS on 'SSR' and reorder columns
        df_secuTrial_w_REVAS = df_secuTrial_w_REVAS.merge(id_log[['SSR', 'FID']], on='SSR', how='left')
        df_secuTrial_w_REVAS.insert(0, 'FID', df_secuTrial_w_REVAS.pop('FID'))  # Move 'FID' to the first column
        
        # Define value mappings
        yes_no_mapping = {0: 'no', 1: 'yes', False: 'no', True: 'yes'}
        bilateral_mapping = {0: 'no', 1: '', 2: 'right', 3: 'left', 4: 'bilateral'}
        prosthetic_valves_mapping = {0: 'None', 1: 'Biological', 2: 'Mechanical'}
        image_type_mapping = {1: 'CT', 2: 'MRI', 3: 'CT (external)', 4: 'MRI (external)'}
        transport_map = {1: 'Ambulance', 2: 'Helicopter', 3: 'Other (taxi,self,relatives,friends...)'}
        discharge_dest_map = {
            1: 'Home', 
            3: 'Rehabilitation Hospital', 
            2: 'Other acute care hospital', 
            4: 'Nursing home, palliative care center, or other medical facility'
        }
        
        # Define common mappings for multiple columns
        yes_no_columns = [
            'flow.iat_stentintracran', 'flow.iat_stentextracran', 'flow.stroke_pre', 
            'flow.tia_pre', 'flow.ich_pre', 'flow.hypertension', 'flow.diabetes',
            'flow.hyperlipidemia', 'flow.smoking', 'flow.atrialfib', 'flow.chd',
            'flow.lowoutput', 'flow.pad', 'flow.decompression', 'img.iat_mech',
            'img.follow_mra', 'img.follow_cta', 'img.follow_ultrasound', 'img.follow_dsa',
            'img.follow_tte', 'img.follow_tee', 'img.follow_holter', 'med.aspirin_pre',
            'med.clopidogrel_pre', 'med.prasugrel_pre', 'med.ticagrelor_pre',
            'med.dipyridamole_pre', 'med.vka_pre', 'med.rivaroxaban_pre',
            'med.dabigatran_pre', 'med.apixaban_pre', 'med.edoxaban_pre',
            'med.parenteralanticg_pre', 'med.antihypertensive_pre', 'med.antilipid_pre',
            'med.hormone_pre', 'med.treat_antiplatelet', 'med.treat_anticoagulant',
            'med.treat_ivt'
        ]
        
        bilateral_columns = ['flow.mca', 'flow.aca', 'flow.pca', 'flow.vertebrobasilar']
        
        # Define value mappings for specific columns
        value_mappings = {
            'enct.non_swiss': {True: 'yes'},
            'enct.sex': {1: 'Male', 2: 'Female'},
            'enct.transport': transport_map,
            'enct.discharge_destinat': discharge_dest_map,
            'flow.firstangio_result': {2: 'no', 3: 'yes'},
            'flow.prostheticvalves': prosthetic_valves_mapping,
            'img.firstimage_type': image_type_mapping,
        }
        
        # Apply yes_no_mapping and bilateral_mapping to multiple columns dynamically
        value_mappings.update({col: yes_no_mapping for col in yes_no_columns})
        value_mappings.update({col: bilateral_mapping for col in bilateral_columns})
        
        # Add DATE column to both datasets
        df_EPIC_all['DATE'] = pd.to_datetime(df_EPIC_all['enct.arrival_date'])
        df_secuTrial_w_REVAS['DATE'] = pd.to_datetime(df_secuTrial_w_REVAS['Arrival at hospital'])
        
        # Load the mapping file
        map_dir = base_dir / 'EPIC2sT-pipeline'
        map_file_name = 'map_epic2sT_code_V2_20250224.xlsx'
        map_file_path = map_dir / map_file_name
        
        if not map_file_path.exists():
            logger.error(f"Mapping file not found: {map_file_path}")
            return
            
        # Load the column mapping Excel file
        df_mapping = pd.read_excel(map_file_path)
        logger.info(f"Loaded mapping file with shape: {df_mapping.shape}")
        
        # Perform the comparison
        logger.info("Starting validation comparison...")
        mismatched_results, comparison_stats, monthly_percentage_stats, variable_stats = compare_epic_secuTrial(
            df_EPIC_all, df_secuTrial_w_REVAS, df_mapping, value_mappings
        )
        
        # Generate timestamp for output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = base_dir / 'EPIC-export-validation/validation-files'
        
        # Save the comparison report
        report = generate_comparison_report(mismatched_results, comparison_stats, monthly_percentage_stats, variable_stats)
        report_path = output_dir / f"validation_report_{timestamp}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {report_path}")
        
        # Restructure the mismatched data for easier viewing
        restructured_df = restructure_mismatched_data(mismatched_results, df_EPIC_all)
        restructured_path = output_dir / f"report_mismatched_values_{timestamp}.xlsx"
        restructured_df.to_excel(restructured_path, index=False)
        logger.info(f"Mismatched values report saved to {restructured_path}")
        
        # Save monthly statistics to Excel
        monthly_stats_df = pd.DataFrame.from_dict(monthly_percentage_stats, orient='index')
        monthly_stats_path = output_dir / f"monthly_validation_stats_{timestamp}.xlsx"
        
        # Create a styled Excel writer
        with pd.ExcelWriter(monthly_stats_path, engine='openpyxl') as writer:
            # Write monthly stats
            monthly_stats_df.to_excel(writer, sheet_name="Monthly_Stats")
            
            # Write overall stats
            pd.DataFrame([comparison_stats]).to_excel(writer, sheet_name="Overall_Stats", index=False)
            
            # Write variable stats
            var_df = pd.DataFrame()
            for var_name, stats in variable_stats.items():
                row = {
                    'Variable': var_name,
                    'Total Comparisons': stats['Total Comparisons'],
                    'Matches': stats['Matches'],
                    'Match Percent': stats['Matching Values (%)'],
                    'Mismatches': stats['Mismatches'],
                    'Mismatch Percent': stats['Mismatched Values (%)'],
                    'EPIC Missing': stats['EPIC Missing'],
                    'EPIC Missing Percent': stats['Values Missing in EPIC (%)'],
                    'SecuTrial Missing': stats['SecuTrial Missing'],
                    'SecuTrial Missing Percent': stats['Values Missing in SecuTrial (%)'],
                    'EPIC Type': stats['EPIC Type'],
                    'SecuTrial Type': stats['SecuTrial Type']
                }
                var_df = pd.concat([var_df, pd.DataFrame([row])], ignore_index=True)
            
            # Sort by mismatch percentage
            var_df = var_df.sort_values(by='Mismatch Percent', ascending=False)
            var_df.to_excel(writer, sheet_name="Variable_Stats", index=False)
        
        logger.info(f"Monthly statistics saved to {monthly_stats_path}")
        
        # Save the original dataframes for reference
        df_EPIC_all.to_excel(output_dir / f"df_EPIC_all_{timestamp}.xlsx", index=False)
        df_secuTrial_w_REVAS.to_excel(output_dir / f"df_secuTrial_w_REVAS_{timestamp}.xlsx", index=False)
        
        logger.info("Validation process completed successfully")
        
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}", exc_info=True)

if __name__ == "__main__":
    main()