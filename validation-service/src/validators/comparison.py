# validation-service/src/validators/comparison.py
"""
Enhanced comparison functions for EPIC-secuTrial validation
Extracted from the notebook for better modularity
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from io import StringIO
from typing import Dict, Any, Optional, Tuple, List, Union
import logging

logger = logging.getLogger(__name__)

def handle_missing_values(x):
    """Handle various missing value representations"""
    if pd.isna(x) or str(x).strip().lower() in ["", "null", "nan", "<na>", "nat"]:
        return np.nan
    return x

def convert_to_bool(x):
    """Convert various representations to boolean"""
    if pd.isna(x) or str(x).strip().lower() in ["", "null", "nan", "<na>", "nat"]:
        return np.nan
    return str(x).strip().lower() in ["true", "yes", "1"]

def safe_datetime_conversion(s, col_name=None, source=None, date_formats=None):
    """
    Converts a column to datetime safely, using specific formats if available.
    """
    if date_formats is None:
        date_formats = {}
        
    # Apply specific formatting if applicable
    if source == "sT" and col_name in date_formats:
        date_format = date_formats[col_name]
    elif source == "ep" and col_name in date_formats:
        date_format = date_formats[col_name]
    else:
        date_format = None  # Use default parsing
    
    return pd.to_datetime(s.astype(str).str.strip(), format=date_format, errors="coerce")

def safe_numeric_conversion(series, dtype):
    """Convert series to numeric type safely."""
    series = series.map(handle_missing_values)
    if dtype == "int":
        return pd.to_numeric(series, errors="coerce").astype("Int64")
    elif dtype == "float":
        return pd.to_numeric(series, errors="coerce").astype(float)
    elif dtype == "float-2":
        return pd.to_numeric(series, errors="coerce").round(2)
    return series

def standardize_boolean_values(value):
    """Standardize boolean values to consistent format"""
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

def convert_value_to_type(value, target_type):
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
        return standardize_boolean_values(value)
    else:
        # Default to string for text, categorical, etc.
        return str(value) if value is not None and value != '' else pd.NA

def values_are_equivalent(val1, val2, target_type):
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
        val1_std = standardize_boolean_values(val1)
        val2_std = standardize_boolean_values(val2)
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

def build_column_mappings(mapping_df):
    """
    Build column mapping dictionary from the mapping DataFrame
    """
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
    
    return column_mappings, column_types

def apply_value_mappings(df, value_mappings):
    """Apply value mappings to DataFrame columns"""
    df_copy = df.copy()
    
    for col, mapping in value_mappings.items():
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].map(lambda x: mapping.get(x, x))
    
    return df_copy

def convert_dataframe_types(df, column_mappings, column_types, data_source='epic'):
    """Convert DataFrame columns to appropriate types"""
    df_copy = df.copy()
    
    for epic_col, secu_col in column_mappings.items():
        if data_source == 'epic' and epic_col in df_copy.columns:
            target_type = column_types[epic_col]['epic_type']
            df_copy[epic_col] = df_copy[epic_col].apply(lambda x: convert_value_to_type(x, target_type))
        elif data_source == 'secuTrial' and secu_col in df_copy.columns:
            target_type = column_types[epic_col]['secu_type']
            df_copy[secu_col] = df_copy[secu_col].apply(lambda x: convert_value_to_type(x, target_type))
    
    return df_copy

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
    
    report = StringIO()
    
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
    if not top_vars.empty:
        report.write(top_vars[['Variable', 'Total Comparisons', 'Match Percent', 'Mismatch Percent', 
                             'EPIC Missing Percent', 'SecuTrial Missing Percent', 'EPIC Type', 'SecuTrial Type']]
                  .to_markdown(index=False))
    else:
        report.write("No problematic variables found.\n")
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

def calculate_monthly_statistics(monthly_stats):
    """Calculate monthly percentage statistics"""
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
    
    return monthly_percentage_stats

def calculate_variable_statistics(variable_stats):
    """Calculate variable-level percentage statistics"""
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
    
    return variable_percentage_stats

def get_default_value_mappings():
    """Get default value mappings for common columns"""
    # Define reusable mappings
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
    
    return value_mappings