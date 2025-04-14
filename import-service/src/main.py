#!/usr/bin/env python3
import os
import sys
import yaml
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Add shared modules to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.utils.file_utils import find_latest_export, safe_read_file, read_and_modify_secuTrial_export
from shared.utils.model_loader import load_models_from_dir, create_mapping_from_models
from shared.mappers.value_mapper import get_value_mappings_from_models
from importers.epic_importer import create_import_file

def main():
    """Main function for the import service"""
    print("Starting EPIC-secuTrial Import Service")
    
    # Load configuration
    config_path = Path("/app/config/import_config.yml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    base_dir = Path(config.get('base_directory', '/app/data'))
    output_dir = base_dir / config.get('output_directory', 'import-files')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load JS models instead of Excel mapping file
    js_models_dir = Path(config.get('models_directory', '/app/models'))
    models = load_models_from_dir(js_models_dir)
    df_mapping_data = create_mapping_from_models(models)
    df_mapping = pd.DataFrame(df_mapping_data)
    
    # Continue with import process using the mapping from JS files
    # (rest of the code remains largely the same)
    # ...

if __name__ == "__main__":
    main()