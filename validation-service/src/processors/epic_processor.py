"""
EPIC file processing module
"""
import pandas as pd
from pathlib import Path
from typing import Optional, List

from ..utils.logger import get_logger
from .file_processor import FileProcessor


class EPICProcessor(FileProcessor):
    """Specialized processor for EPIC files"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize EPIC processor"""
        super().__init__(base_dir)
        self.logger = get_logger('epic-processor')
    
    def find_merge_column(self, directory: Path) -> Optional[str]:
        """
        Find the correct merge column by checking the first file
        
        Args:
            directory: Directory containing EPIC files
            
        Returns:
            Name of merge column or None
        """
        file_patterns = ["*.xlsx", "*.xls", "*.csv"]
        all_files = [f for pattern in file_patterns for f in directory.glob(pattern)]
        
        if not all_files:
            self.logger.error(f"No data files found in {directory}")
            return None
        
        # Check first file for common merge columns
        first_file = all_files[0]
        df = self.safe_read_file(first_file)
        
        if df is None or len(df.columns) <= 1:
            self.logger.error(f"Could not read or empty file: {first_file}")
            return None
        
        # Try common merge column names
        possible_columns = ['PAT_ENC_CSN_ID', 'PatientID', 'ID', 'Patient_ID', 'CSN_ID']
        for col in possible_columns:
            if col in df.columns:
                self.logger.info(f"Found merge column: {col}")
                return col
        
        # Look for ID-like columns
        for col in df.columns:
            if any(word in col.upper() for word in ['ID', 'CSN', 'PATIENT']):
                self.logger.info(f"Using merge column: {col}")
                return col
        
        self.logger.warning(f"No suitable merge column found. Available: {list(df.columns)}")
        return 'PAT_ENC_CSN_ID'  # Default fallback
    
    def get_file_prefix(self, filename: str) -> str:
        """
        Get column prefix based on EPIC file type
        
        Args:
            filename: Name of the file
            
        Returns:
            Appropriate prefix string
        """
        name = filename.lower()
        if 'enc' in name: 
            return 'enct.'
        elif 'flow' in name: 
            return 'flow.'
        elif 'imag' in name or 'img' in name: 
            return 'img.'
        elif 'lab' in name: 
            return 'lab.'
        elif 'med' in name: 
            return 'med.'
        elif 'mon' in name: 
            return 'mon.'
        else:
            return ""
    
    def merge_single_epic_file(self, file_path: Path, merge_column: str, 
                              merged_df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
        """
        Merge a single EPIC file into the main DataFrame
        
        Args:
            file_path: Path to the EPIC file
            merge_column: Column to merge on
            merged_df: Existing merged dataframe
            prefix: Prefix to add to column names
            
        Returns:
            Updated merged dataframe
        """
        df = self.safe_read_file(file_path)
        if df is None:
            self.logger.warning(f"Failed to read {file_path.name}")
            return merged_df
        
        if merge_column not in df.columns:
            self.logger.warning(f"Merge column '{merge_column}' not found in {file_path.name}")
            self.logger.info(f"Available columns: {list(df.columns)}")
            return merged_df
        
        # Add prefix to all columns except the merge column
        if prefix:
            df = df.rename(columns={col: f"{prefix}{col}" 
                                  for col in df.columns if col != merge_column})
        
        # Merge logic
        if merged_df.empty:
            result_df = df.copy()
            self.logger.info(f"Using {file_path.name} as base: shape={result_df.shape}")
        else:
            result_df = merged_df.merge(df, on=merge_column, how="outer")
            self.logger.info(f"Merged {file_path.name}: {df.shape} → total={result_df.shape}")
        
        return result_df
    
    def load_and_merge_epic_files(self) -> Optional[pd.DataFrame]:
        """
        Load and merge all EPIC files from the latest export
        
        Returns:
            Merged EPIC dataframe or None
        """
        self.logger.info("Loading and merging EPIC files...")
        
        # Find latest EPIC export
        latest_epic_export = self.find_latest_export('EPIC-files')
        if not latest_epic_export:
            return None
        
        # Get all data files
        file_patterns = ["*.xlsx", "*.xls", "*.csv"]
        all_files = [f for pattern in file_patterns for f in latest_epic_export.glob(pattern)]
        
        if not all_files:
            self.logger.error(f"No data files found in {latest_epic_export}")
            return None
        
        self.logger.info(f"Found {len(all_files)} data files in {latest_epic_export.name}")
        
        # Auto-detect merge column
        merge_column = self.find_merge_column(latest_epic_export)
        if not merge_column:
            self.logger.error("Could not find a suitable merge column")
            return None
        
        # Define file processing order (encounters first, then others)
        file_order = ['enc', 'flow', 'imag', 'img', 'lab', 'med', 'mon']
        
        def file_priority(file_path: Path) -> int:
            """Determine processing priority for file"""
            name = file_path.stem.lower()
            for i, keyword in enumerate(file_order):
                if keyword in name:
                    return i
            return len(file_order)  # Unknown files go last
        
        # Sort files by priority
        sorted_files = sorted(all_files, key=file_priority)
        
        # Merge all files
        merged_df = pd.DataFrame()
        for file_path in sorted_files:
            prefix = self.get_file_prefix(file_path.stem)
            merged_df = self.merge_single_epic_file(file_path, merge_column, merged_df, prefix)
        
        if not merged_df.empty:
            self.logger.info(f"Final merged EPIC DataFrame shape: {merged_df.shape}")
            
            # Save merged data for reference
            output_dir = self.base_dir / "EPIC-export-validation/validation-files"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"merged_epic_data_{timestamp}.csv"
            merged_df.to_csv(output_path, index=False)
            self.logger.info(f"Merged EPIC data saved to: {output_path}")
        
        return merged_df