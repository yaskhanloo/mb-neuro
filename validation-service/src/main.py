#!/usr/bin/env python3
"""
EPIC-secuTrial Validation Service
Clean, modular implementation converted from Jupyter notebook

Created by: Yasaman Safarkhanlo
Last modified: Step-by-step implementation for Docker
"""

import sys
import os
from pathlib import Path
from typing import Tuple, Optional

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from validation_service.src.utils.logger import setup_logger
from validation_service.src.processors.file_processor import FileProcessor
from validation_service.src.processors.epic_processor import EPICProcessor
from validation_service.src.processors.patient_matcher import PatientMatcher


def main():
    """Main validation workflow"""
    # Initialize logging
    logger = setup_logger('validation-main')
    
    try:
        logger.info("=" * 60)
        logger.info("Starting EPIC-secuTrial Validation Service")
        logger.info("=" * 60)
        
        # Get base directory
        base_dir = Path(os.environ.get("BASE_DIR", "."))
        logger.info(f"Using base directory: {base_dir}")
        
        # Step 1: Load secuTrial files
        logger.info("\n" + "="*40)
        logger.info("STEP 1: Loading secuTrial Files")
        logger.info("="*40)
        
        file_processor = FileProcessor(base_dir)
        df_secuTrial, df_REVASC = file_processor.load_secuTrial_files()
        
        if df_secuTrial is None or df_REVASC is None:
            logger.error("Failed to load secuTrial files")
            sys.exit(1)
        
        # Merge secuTrial with REVASC
        df_secuTrial_merged = file_processor.merge_secuTrial_with_REVASC(df_secuTrial, df_REVASC)
        
        # Step 2: Load and merge EPIC files
        logger.info("\n" + "="*40)
        logger.info("STEP 2: Loading and Merging EPIC Files")
        logger.info("="*40)
        
        epic_processor = EPICProcessor(base_dir)
        df_epic_merged = epic_processor.load_and_merge_epic_files()
        
        if df_epic_merged is None:
            logger.error("Failed to load and merge EPIC files")
            sys.exit(1)
        
        # Step 3: Patient matching
        logger.info("\n" + "="*40)
        logger.info("STEP 3: Patient Matching Process")
        logger.info("="*40)
        
        patient_matcher = PatientMatcher(base_dir)
        output_dir = base_dir / 'EPIC-export-validation/validation-files'
        id_log_path = base_dir / 'EPIC2sT-pipeline/Identification_log_SSR_2024_ohne PW_26.03.25.xlsx'
        
        df_epic_common, df_secuTrial_common = patient_matcher.process_patient_matching(
            df_epic_merged, 
            df_secuTrial_merged, 
            id_log_path, 
            output_dir
        )
        
        # Step 4: Summary
        logger.info("\n" + "="*40)
        logger.info("STEP 4: Process Summary")
        logger.info("="*40)
        
        logger.info(f"✅ SecuTrial data loaded: {df_secuTrial_merged.shape}")
        logger.info(f"✅ EPIC data merged: {df_epic_merged.shape}")
        logger.info(f"✅ Common patients found: EPIC={df_epic_common.shape}, secuTrial={df_secuTrial_common.shape}")
        
        # Next steps placeholder
        logger.info("\n" + "="*40)
        logger.info("NEXT STEPS")
        logger.info("="*40)
        logger.info("🔄 Ready for comparison logic implementation")
        logger.info("📊 Patient matching analysis saved to output directory")
        logger.info("🎯 Validation service core functionality completed")
        
        logger.info("\n" + "="*60)
        logger.info("EPIC-secuTrial Validation Service Completed Successfully!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Validation service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()