import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

def extract_model_definition(js_file_path: Path) -> Dict[str, Any]:
    """
    Extracts model definition from a Sequelize model JS file.
    
    Args:
        js_file_path: Path to the JS model file
        
    Returns:
        Dictionary containing the extracted field definitions
    """
    with open(js_file_path, 'r') as f:
        js_content = f.read()
    
    # Extract the model definition
    model_match = re.search(r'sequelize\.define\([\'"](\w+)[\'"],\s*{([^}]+)}', js_content, re.DOTALL)
    if not model_match:
        raise ValueError(f"Could not extract model definition from {js_file_path}")
    
    model_name = model_match.group(1)
    fields_text = model_match.group(2)
    
    # Parse field definitions
    field_pattern = re.compile(r'(\w+):\s*{([^}]+)}', re.DOTALL)
    field_matches = field_pattern.findall(fields_text)
    
    fields = {}
    for field_name, field_def in field_matches:
        # Extract type
        type_match = re.search(r'type:\s*DataTypes\.(\w+)', field_def)
        if type_match:
            data_type = type_match.group(1)
            
            # Map Sequelize types to Python/pandas types
            type_mapping = {
                'STRING': 'str',
                'TEXT': 'str',
                'INTEGER': 'int',
                'FLOAT': 'float',
                'DOUBLE': 'float',
                'DECIMAL': 'float',
                'BOOLEAN': 'bool',
                'DATE': 'datetime',
                'DATEONLY': 'date',
                'TIME': 'time',
                'BIGINT': 'int'
            }
            
            python_type = type_mapping.get(data_type, 'str')
            
            # Check if field is required
            is_required = 'allowNull: false' in field_def and 'primaryKey: true' not in field_def
            
            fields[field_name] = {
                'type': python_type,
                'required': is_required,
                'primaryKey': 'primaryKey: true' in field_def,
                'autoIncrement': 'autoIncrement: true' in field_def
            }
    
    return {
        'model_name': model_name,
        'fields': fields
    }

def load_models_from_dir(models_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Loads all model definitions from a directory of JS files.
    
    Args:
        models_dir: Directory containing JS model files
        
    Returns:
        Dictionary mapping model names to their definitions
    """
    models = {}
    
    for js_file in models_dir.glob('*.js'):
        try:
            model_def = extract_model_definition(js_file)
            models[model_def['model_name']] = model_def
        except Exception as e:
            print(f"Error processing {js_file}: {e}")
    
    return models

def create_mapping_from_models(models: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Creates a mapping configuration similar to what would be in the Excel file.
    
    Args:
        models: Dictionary of model definitions
        
    Returns:
        List of mapping entries for EPIC to secuTrial conversion
    """
    mappings = []
    
    # Define prefixes for different model types
    model_prefixes = {
        'epic_encounter': 'enct',
        'stroke_flowsheet': 'flow',
        'stroke_lab_data': 'lab',
        'stroke_image_data': 'img',
        'stroke_medication': 'med',
        'stroke_monitor': 'mon'
    }
    
    for model_name, model_def in models.items():
        # Skip models that aren't relevant for the EPIC-secuTrial mapping
        if model_name not in model_prefixes and not model_name.startswith('epic_'):
            continue
        
        # Determine the prefix based on model name
        prefix = next((v for k, v in model_prefixes.items() if model_name.startswith(k)), '')
        
        # Extract secuTrial table name
        secuTrial_table = 'Acute'  # Default table
        if 'flowsheet' in model_name:
            secuTrial_table = 'Acute'
        elif 'lab' in model_name:
            secuTrial_table = 'LabData'
        elif 'image' in model_name:
            secuTrial_table = 'ImageData'
        elif 'medication' in model_name:
            secuTrial_table = 'Medication'
        
        # Create mapping for each field
        for field_name, field_def in model_def['fields'].items():
            # Skip internal fields
            if field_name in ['id', 'idCase', 'idPatient', 'createdAt', 'updatedAt']:
                continue
                
            mapping = {
                'EPIC_exportFileName': model_name.replace('_', ' ').title(),
                'EPIC_table': model_name,
                'EPIC_field': field_name,
                'EPIC_varColumnName': field_name,
                'EPIC_varType': field_def['type'],
                'secuTrial_import_table': secuTrial_table,
                'secuTrial_import_field': field_name,
                'sT_varColumnName': field_name,
                'sT_varType': field_def['type']
            }
            
            mappings.append(mapping)
    
    return mappings