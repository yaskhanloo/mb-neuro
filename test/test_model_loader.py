#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import pandas as pd
from shared.utils.model_loader import load_models_from_dir, create_mapping_from_models
from shared.mappers.value_mapper import get_value_mappings_from_models
import json

# Path to JS model files
models_dir = project_root / "models"

# Make sure the models directory exists
if not models_dir.exists():
    print(f"Models directory not found: {models_dir}")
    print("Creating models directory...")
    models_dir.mkdir(exist_ok=True)
    
    # If no models exist yet, copy the example model to this directory
    if len(list(models_dir.glob('*.js'))) == 0:
        print("No models found. Make sure to copy your JS model files to the models directory.")
        sys.exit(1)

print(f"Looking for JS models in: {models_dir}")

# Load models
models = load_models_from_dir(models_dir)
print(f"Loaded {len(models)} models")

# Create mapping from models
mappings = create_mapping_from_models(models)
print(f"Generated {len(mappings)} mapping entries")

# Convert to DataFrame and display
df_mapping = pd.DataFrame(mappings)
print("\nMapping columns:")
print(df_mapping.columns.tolist())
print("\nSample mapping entries:")
if not df_mapping.empty:
    print(df_mapping.head(3).to_string())
else:
    print("No mapping entries were generated.")

# Get value mappings
value_mappings = get_value_mappings_from_models(models_dir)
print("\nExtracted value mappings:")
for mapping_name, mapping in value_mappings.items():
    print(f"- {mapping_name}: {list(mapping.items())[:3]}...")