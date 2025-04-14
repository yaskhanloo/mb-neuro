import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Union, Optional

def create_import_file(df_EPIC, dictionary, start_id=13744):
    """
    Creates a DataFrame for import into secuTrial using values mapped from EPIC data.
    
    Args:
        df_EPIC (DataFrame): The EPIC dataset
        dictionary (Path or str): Path to the mapping dictionary Excel file
        start_id (int): Starting ID for SSR cases
        
    Returns:
        DataFrame: DataFrame formatted for secuTrial import
    """
    # Load the mapping file and initialize the import DataFrame
    mapping_df = pd.read_excel(dictionary)
    today_date = datetime.today().date()

    df_import = pd.DataFrame({
        'case_id': [f'SSR-INS-{i}' for i in range(start_id, start_id + len(df_EPIC))],
        'visit_name': ["Acute Phase"] * len(df_EPIC),
        'center_id': ["Bern Inselspital (SSR)"] * len(df_EPIC),
        'entry_date': [today_date] * len(df_EPIC)
    })

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

    return df_import