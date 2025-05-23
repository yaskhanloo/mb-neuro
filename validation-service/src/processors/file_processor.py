"""
File processing module for EPIC-secuTrial validation service
"""
import os
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime

from ..utils.logger import get_logger


class FileProcessor:
    """Handles file loading and processing for EPIC and secuTrial data"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize FileProcessor
        
        Args:
            base_dir: Base directory for data files (defaults to BASE_DIR env var)
        """
        self.logger = get_logger('file-processor')
        self.base_dir = base_dir or Path(os.getenv('BASE_DIR', '.'))
        self.logger.info(f"FileProcessor initialized with base_dir: {self.base_dir}")
    
    def find_latest_export(self, export_type: str) -> Optional[Path]:
        """
        Find the latest export directory for given type
        
        Args:
            export_type: Either 'EPIC-files' or 'sT-files'
            
        Returns:
            Path to latest export directory or None
        """
        export_dir = self.base_dir / export_type
        if not export_dir.exists():
            self.logger.error(f"Export directory does not exist: {export_dir}")
            return None
            
        export_dirs = list(export_dir.glob("export-*"))
        if not export_dirs:
            self.logger.error(f"No export directories found in {export_dir}")
            return None
            
        latest = max(export_dirs, key=lambda x: x.stat().st_mtime)
        self.logger.info(f"Latest {export_type} export found: {latest}")
        return latest
    
    def safe_read_file(self, file_path: Path, custom_reader=None) -> Optional[pd.DataFrame]:
        """
        Safely read a file (Excel or CSV) with error handling
        
        Args:
            file_path: Path to the file
            custom_reader: Optional custom processing function
            
        Returns:
            DataFrame or None if failed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return None
            
        file_extension = file_path.suffix.lower()
        self.logger.info(f"Reading file: {file_path.name}")
        
        try:
            # Read based on file type
            if file_extension in [".xlsx", ".xls"]:
                if custom_reader:
                    df = pd.read_excel(file_path, 
                                     engine='openpyxl' if file_extension == ".xlsx" else 'xlrd', 
                                     header=None)
                else:
                    df = pd.read_excel(file_path, 
                                     engine='openpyxl' if file_extension == ".xlsx" else 'xlrd')
            elif file_extension == ".csv":
                df = self._read_csv_with_fallback(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Apply custom reader if provided
            if custom_reader:
                df = custom_reader(df)
            
            if df is None or df.empty:
                self.logger.warning(f"{file_path.name} is empty after processing")
                return None
                
            self.logger.info(f"Successfully read {file_path.name}: shape={df.shape}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def _read_csv_with_fallback(self, file_path: Path) -> pd.DataFrame:
        """Read CSV with multiple encoding/separator fallbacks"""
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        separators = [',', '\t', ';', '|']
        
        for encoding in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=sep, on_bad_lines='skip')
                    if len(df.columns) > 1:  # Good separator found
                        self.logger.info(f"CSV read successfully with encoding={encoding}, sep='{sep}'")
                        return df
                except Exception:
                    continue
        
        # Final fallback
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            self.logger.info("CSV read with default UTF-8 encoding")
            return df
        except Exception as e:
            raise ValueError(f"Could not read CSV with any encoding/separator: {e}")
    
    def read_and_modify_secuTrial_export(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process secuTrial export by removing metadata rows and setting proper headers
        
        Args:
            df: Raw dataframe from secuTrial export
            
        Returns:
            Processed dataframe
        """
        try:
            # secuTrial exports have metadata in first 6 rows
            processed_df = (df.iloc[6:]  # Skip first 6 rows
                           .pipe(lambda x: x.set_axis(x.iloc[0], axis=1))  # Use row 6 as header
                           .iloc[1:]  # Drop the header row
                           .reset_index(drop=True)  # Reset index
                           .dropna(how='all'))  # Remove completely empty rows
            
            self.logger.info(f"SecuTrial export processed: {df.shape} → {processed_df.shape}")
            return processed_df
            
        except Exception as e:
            self.logger.error(f"Error processing secuTrial export: {e}")
            return df
    
    def load_secuTrial_files(self) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Load secuTrial and REVASC files
        
        Returns:
            Tuple of (secuTrial_df, REVASC_df)
        """
        self.logger.info("Loading secuTrial files...")
        
        # Find latest secuTrial export
        latest_sT_export = self.find_latest_export('sT-files')
        if not latest_sT_export:
            return None, None
        
        # Define file paths
        secuTrial_file = latest_sT_export / 'SSR_cases_of_2024.xlsx'
        revasc_file = latest_sT_export / 'REVASC' / 'report_SSR01_20250218-105747.xlsx'
        
        # Read files with custom processor
        df_secuTrial = self.safe_read_file(secuTrial_file, 
                                          custom_reader=self.read_and_modify_secuTrial_export)
        df_REVASC = self.safe_read_file(revasc_file, 
                                       custom_reader=self.read_and_modify_secuTrial_export)
        
        if df_secuTrial is not None and df_REVASC is not None:
            self.logger.info(f"secuTrial files loaded: secuTrial={df_secuTrial.shape}, REVASC={df_REVASC.shape}")
        
        return df_secuTrial, df_REVASC
    
    def merge_secuTrial_with_REVASC(self, df_secuTrial: pd.DataFrame, 
                                   df_REVASC: pd.DataFrame) -> pd.DataFrame:
        """
        Merge REVASC data into secuTrial DataFrame
        
        Args:
            df_secuTrial: Main secuTrial dataframe
            df_REVASC: REVASC dataframe to merge
            
        Returns:
            Merged dataframe
        """
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
            
            self.logger.info(f"Successfully merged secuTrial + REVASC: {merged_df.shape}")
            return merged_df
            
        except Exception as e:
            self.logger.error(f"REVASC merge failed: {e}. Using secuTrial data only.")
            return df_secuTrial.copy()