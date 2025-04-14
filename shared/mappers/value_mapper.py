from typing import Dict, Any, List, Optional
import re

def extract_value_mappings_from_js(js_file_path):
    """Extract value mappings defined in JS files"""
    with open(js_file_path, 'r') as f:
        js_content = f.read()
    
    # Find mapping definitions
    mappings = {}
    
    # Look for common mapping patterns in the JS file
    # Example: {1: 'Ambulance', 2: 'Helicopter', 3: 'Other...'}
    mapping_pattern = re.compile(r'(\w+)_MAP(?:PING)?\s*=\s*{([^}]+)}', re.DOTALL)
    for name, definition in mapping_pattern.findall(js_content):
        # Parse the key-value pairs
        pairs = {}
        for pair in re.findall(r'(\d+|true|false):\s*[\'"]([^\'"]+)[\'"]', definition):
            key = pair[0]
            # Convert string boolean/numbers to Python types
            if key == 'true':
                key = True
            elif key == 'false':
                key = False
            else:
                key = int(key)
            pairs[key] = pair[1]
        
        mappings[name.lower()] = pairs
    
    return mappings

def get_value_mappings_from_models(model_dir):
    """Generate value mappings from model definitions"""
    # Standard mappings
    mappings = {
        'yes_no_mapping': {0: 'no', 1: 'yes', False: 'no', True: 'yes'},
        'bilateral_mapping': {0: 'no', 1: '', 2: 'right', 3: 'left', 4: 'bilateral'},
        'prosthetic_valves_mapping': {0: 'None', 1: 'Biological', 2: 'Mechanical'},
        'image_type_mapping': {1: 'CT', 2: 'MRI', 3: 'CT (external)', 4: 'MRI (external)'},
        'transport_map': {1: 'Ambulance', 2: 'Helicopter', 3: 'Other (taxi,self,relatives,friends...)'},
        'discharge_dest_map': {
            1: 'Home', 
            3: 'Rehabilitation Hospital', 
            2: 'Other acute care hospital', 
            4: 'Nursing home, palliative care center, or other medical facility'
        }
    }
    
    # Extract additional mappings from JS files
    for js_file in model_dir.glob('*.js'):
        try:
            file_mappings = extract_value_mappings_from_js(js_file)
            mappings.update(file_mappings)
        except Exception as e:
            print(f"Error extracting mappings from {js_file}: {e}")
    
    # Define which columns use which mappings
    column_mappings = {}
    
    # Boolean columns (yes/no)
    boolean_columns = [
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
        'med.treat_ivt', 'enct.non_swiss'
    ]
    
    # Add mappings for specific columns
    for col in boolean_columns:
        column_mappings[col] = mappings['yes_no_mapping']
    
    # Bilateral columns
    bilateral_columns = ['flow.mca', 'flow.aca', 'flow.pca', 'flow.vertebrobasilar']
    for col in bilateral_columns:
        column_mappings[col] = mappings['bilateral_mapping']
    
    # Add specific column mappings
    column_mappings['enct.sex'] = {1: 'Male', 2: 'Female'}
    column_mappings['enct.transport'] = mappings['transport_map']
    column_mappings['enct.discharge_destinat'] = mappings['discharge_dest_map']
    column_mappings['flow.prostheticvalves'] = mappings['prosthetic_valves_mapping']
    column_mappings['img.firstimage_type'] = mappings['image_type_mapping']
    
    return column_mappings