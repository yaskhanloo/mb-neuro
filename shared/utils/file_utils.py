import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

def find_latest_export(base_dir: Path, pattern: str) -> Optional[Path]:
    """Find the latest export directory matching a pattern"""
    exports = list(base_dir.glob(pattern))
    if not exports:
        return None
    return max(exports, key=lambda x: x.stat().st_mtime)

def read_and_modify_secuTrial_export(df: pd.DataFrame) -> pd.DataFrame:
    """Process secuTrial export dataframe"""
    df = df.drop([7])                   # Remove row 8 in Excel
    df = df.iloc[6:]                    # Skip the first 6 rows
    df.columns = df.iloc[0]             # Use row 6 as the header
    df = df[1:].reset_index(drop=True)  # Drop the header row and reset index
    return df

def safe_read_file(file_path: Path, custom_reader=None) -> Optional[pd.DataFrame]:
    """Safely read a file (Excel or CSV) with an optional custom reader function"""
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
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"Error reading file at {file_path}: {e}")
    
    return None