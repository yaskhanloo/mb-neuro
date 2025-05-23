"""
Patient matching module for EPIC and secuTrial data
"""
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime

from ..utils.logger import get_logger
from .file_processor import FileProcessor


class PatientMatcher(FileProcessor):
    """Handles patient ID matching between EPIC and secuTrial data"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize PatientMatcher"""
        super().__init__(base_dir)
        self.logger = get_logger('patient-matcher')
    
    def load_and_process_id_log(self, id_log_path: Path) -> Optional[pd.DataFrame]:
        """
        Load and process the ID mapping log file
        
        Args:
            id_log_path: Path to the ID log Excel file
            
        Returns:
            Processed ID log dataframe or None
        """
        try:
            self.logger.info(f"Loading ID log from: {id_log_path}")
            id_log = pd.read_excel(id_log_path)
            self.logger.info(f"ID log original columns: {list(id_log.columns)}")
            
            # Set first row as headers (secuTrial export format)
            id_log.columns = id_log.iloc[0]
            id_log = id_log.iloc[1:].reset_index(drop=True)
            self.logger.info(f"ID log columns after header fix: {list(id_log.columns)}")
            
            # Map actual column names to standard names
            column_mapping = {}
            for col in id_log.columns:
                if pd.isna(col):  # Skip NaN columns
                    continue
                col_str = str(col).strip()
                if 'Fall-Nr.' in col_str:
                    column_mapping[col] = 'FID'
                elif 'SSR Identification' in col_str:
                    column_mapping[col] = 'SSR'
            
            self.logger.info(f"Column mapping: {column_mapping}")
            id_log.rename(columns=column_mapping, inplace=True)
            
            # Remove NaN columns
            id_log = id_log.loc[:, ~id_log.columns.isna()]
            
            # Validate required columns
            if 'FID' not in id_log.columns or 'SSR' not in id_log.columns:
                self.logger.error(f"Required columns not found. Available: {list(id_log.columns)}")
                self.logger.error("Expected to find 'Fall-Nr.' and 'SSR Identification' columns")
                return None
            
            # Convert to appropriate data types
            id_log['FID'] = pd.to_numeric(id_log['FID'], errors='coerce')
            id_log['SSR'] = pd.to_numeric(id_log['SSR'], errors='coerce')
            
            # Remove rows with missing FID or SSR
            initial_count = len(id_log)
            id_log = id_log.dropna(subset=['FID', 'SSR'])
            final_count = len(id_log)
            
            if final_count < initial_count:
                self.logger.warning(f"Removed {initial_count - final_count} rows with missing FID/SSR")
            
            self.logger.info(f"Loaded ID log with {final_count} valid entries")
            return id_log
            
        except Exception as e:
            self.logger.error(f"Failed to load ID log: {e}")
            return None
    
    def add_patient_ids(self, df_epic: pd.DataFrame, df_secuTrial: pd.DataFrame, 
                       id_log: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Add FID and SSR columns to both dataframes
        
        Args:
            df_epic: EPIC dataframe
            df_secuTrial: secuTrial dataframe
            id_log: ID mapping dataframe
            
        Returns:
            Tuple of (updated_epic_df, updated_secuTrial_df)
        """
        self.logger.info("Adding patient IDs to dataframes...")
        
        # Work with copies to avoid modifying originals
        df_epic = df_epic.copy()
        df_secuTrial = df_secuTrial.copy()
        
        # Add FID to EPIC data
        if 'img.FID' in df_epic.columns:
            df_epic['FID'] = df_epic['img.FID'].fillna(0).astype(int)
            df_epic.insert(0, 'FID', df_epic.pop('FID'))
            self.logger.info("Added FID to EPIC data from img.FID column")
        else:
            self.logger.warning("img.FID column not found in EPIC data")
        
        # Add SSR to secuTrial data (extract from Case ID)
        if 'Case ID' in df_secuTrial.columns:
            df_secuTrial['SSR'] = df_secuTrial['Case ID'].str.extract(r'(\\d+)$').astype(int)
            df_secuTrial.insert(1, 'SSR', df_secuTrial.pop('SSR'))
            # Clean up any 'nan' columns
            df_secuTrial = df_secuTrial.drop(columns=['nan'], errors='ignore')
            self.logger.info("Added SSR to secuTrial data from Case ID")
        else:
            self.logger.warning("Case ID column not found in secuTrial data")
        
        # Merge with ID log to get complete ID mappings
        if id_log is not None:
            # Validate ID log has required columns
            if 'FID' not in id_log.columns:
                self.logger.error(f"FID column not found in ID log. Available: {list(id_log.columns)}")
                return df_epic, df_secuTrial
            
            if 'SSR' not in id_log.columns:
                self.logger.error(f"SSR column not found in ID log. Available: {list(id_log.columns)}")
                return df_epic, df_secuTrial
            
            # Merge EPIC with ID log (FID → SSR)
            if 'FID' in df_epic.columns:
                df_epic = df_epic.merge(id_log[['FID', 'SSR']], on='FID', how='left')
                df_epic.insert(1, 'SSR', df_epic.pop('SSR'))
                self.logger.info("Merged EPIC with ID log")
            
            # Merge secuTrial with ID log (SSR → FID)
            if 'SSR' in df_secuTrial.columns:
                df_secuTrial = df_secuTrial.merge(id_log[['SSR', 'FID']], on='SSR', how='left')
                df_secuTrial.insert(0, 'FID', df_secuTrial.pop('FID'))
                self.logger.info("Merged secuTrial with ID log")
            
            self.logger.info("Successfully added patient IDs to both dataframes")
        
        return df_epic, df_secuTrial
    
    def find_matching_patients(self, df_epic: pd.DataFrame, 
                             df_secuTrial: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Find patients that exist in both datasets
        
        Args:
            df_epic: EPIC dataframe with FID/SSR
            df_secuTrial: secuTrial dataframe with FID/SSR
            
        Returns:
            Tuple of (epic_common, secuTrial_common)
        """
        # Find common patients by FID and SSR
        common_keys = df_secuTrial[['FID', 'SSR']].merge(
            df_epic[['FID', 'SSR']], 
            on=['FID', 'SSR'], 
            how='inner'
        )
        
        # Filter to matching patients only
        df_epic_common = df_epic.merge(common_keys, on=['FID', 'SSR'], how='inner')
        df_secuTrial_common = df_secuTrial.merge(common_keys, on=['FID', 'SSR'], how='inner')
        
        self.logger.info(f"Found {len(common_keys)} matching patients")
        self.logger.info(f"EPIC common shape: {df_epic_common.shape}")
        self.logger.info(f"secuTrial common shape: {df_secuTrial_common.shape}")
        
        return df_epic_common, df_secuTrial_common
    
    def find_missing_patients(self, df_epic: pd.DataFrame, 
                            df_secuTrial: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Find patients that exist in only one dataset
        
        Args:
            df_epic: EPIC dataframe with FID/SSR
            df_secuTrial: secuTrial dataframe with FID/SSR
            
        Returns:
            Tuple of (secuTrial_only, epic_only)
        """
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
        
        self.logger.info(f"Patients only in secuTrial: {len(df_secuTrial_only)}")
        self.logger.info(f"Patients only in EPIC: {len(df_epic_only)}")
        
        return df_secuTrial_only, df_epic_only
    
    def save_patient_analysis(self, df_epic_common: pd.DataFrame, df_secuTrial_common: pd.DataFrame,
                            df_epic_only: pd.DataFrame, df_secuTrial_only: pd.DataFrame,
                            output_dir: Path) -> None:
        """
        Save patient matching analysis to Excel files
        
        Args:
            df_epic_common: Common patients in EPIC
            df_secuTrial_common: Common patients in secuTrial
            df_epic_only: Patients only in EPIC
            df_secuTrial_only: Patients only in secuTrial
            output_dir: Directory to save analysis files
        """
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
        
        self.logger.info(f"Patient analysis saved to {common_file} and {missing_file}")
    
    def process_patient_matching(self, df_epic: pd.DataFrame, df_secuTrial: pd.DataFrame,
                               id_log_path: Path, output_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Complete patient matching workflow
        
        Args:
            df_epic: EPIC dataframe
            df_secuTrial: secuTrial dataframe
            id_log_path: Path to ID mapping log
            output_dir: Output directory for analysis files
            
        Returns:
            Tuple of (epic_common, secuTrial_common) - datasets with only matching patients
        """
        self.logger.info("Starting patient matching process...")
        
        # Load ID log
        id_log = self.load_and_process_id_log(id_log_path)
        if id_log is None:
            self.logger.warning("ID log failed to load, returning original data")
            return df_epic, df_secuTrial
        
        # Add patient IDs
        df_epic, df_secuTrial = self.add_patient_ids(df_epic, df_secuTrial, id_log)
        
        # Find matching and missing patients
        df_epic_common, df_secuTrial_common = self.find_matching_patients(df_epic, df_secuTrial)
        df_secuTrial_only, df_epic_only = self.find_missing_patients(df_epic, df_secuTrial)
        
        # Save analysis
        self.save_patient_analysis(df_epic_common, df_secuTrial_common, 
                                 df_epic_only, df_secuTrial_only, output_dir)
        
        self.logger.info("Patient matching process completed successfully!")
        return df_epic_common, df_secuTrial_common