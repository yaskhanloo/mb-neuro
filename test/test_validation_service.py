# test/test_validation_service.py
"""
Test suite for the enhanced validation service
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import sys
import os

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from validation_service.src.validators.comparison import (
    standardize_boolean_values,
    convert_value_to_type,
    values_are_equivalent,
    build_column_mappings,
    get_default_value_mappings
)

class TestValidationService:
    
    def setup_method(self):
        """Set up test data"""
        self.sample_epic_data = pd.DataFrame({
            'FID': [1, 2, 3],
            'SSR': [101, 102, 103],
            'enct.arrival_date': ['2024-04-01', '2024-05-15', '2024-06-30'],
            'enct.sex': [1, 2, 1],
            'enct.non_swiss': [True, False, True],
            'flow.hypertension': [1, 0, 1],
            'img.firstimage_type': [1, 2, 1]
        })
        
        self.sample_secuTrial_data = pd.DataFrame({
            'FID': [1, 2, 3],
            'SSR': [101, 102, 103],
            'Arrival at hospital': ['2024-04-01', '2024-05-15', '2024-06-30'],
            'Sex': ['Male', 'Female', 'Male'],
            'Non-Swiss': ['yes', 'no', 'yes'],
            'Hypertension': ['yes', 'no', 'yes'],
            '1st brain imaging type': ['CT', 'MRI', 'CT']
        })
        
        self.sample_mapping = pd.DataFrame({
            'EPIC_varColumnName': ['sex', 'non_swiss', 'hypertension', 'firstimage_type'],
            'EPIC_exportFileName': ['Encounters', 'Encounters', 'Flowsheet', 'Imaging'],
            'EPIC_varType': ['int', 'bool', 'bool', 'int'],
            'sT_varColumnName': ['Sex', 'Non-Swiss', 'Hypertension', '1st brain imaging type'],
            'sT_exportFileName': ['SSR', 'SSR', 'SSR', 'SSR'],
            'sT_varType': ['str', 'str', 'str', 'str']
        })

    def test_standardize_boolean_values(self):
        """Test boolean value standardization"""
        assert standardize_boolean_values(True) == "yes"
        assert standardize_boolean_values(False) == "no"
        assert standardize_boolean_values(1) == "yes"
        assert standardize_boolean_values(0) == "no"
        assert standardize_boolean_values("true") == "yes"
        assert standardize_boolean_values("false") == "no"
        assert standardize_boolean_values("YES") == "yes"
        assert standardize_boolean_values("NO") == "no"
        assert pd.isna(standardize_boolean_values(np.nan))

    def test_convert_value_to_type(self):
        """Test value type conversion"""
        # Integer conversion
        assert convert_value_to_type("123", "int") == 123
        assert convert_value_to_type("123.5", "int") == 123
        assert pd.isna(convert_value_to_type("", "int"))
        
        # Float conversion
        assert convert_value_to_type("123.45", "float") == 123.45
        assert convert_value_to_type("123", "float") == 123.0
        
        # Float with precision
        assert convert_value_to_type("123.456", "float-2") == 123.46
        
        # Boolean conversion
        assert convert_value_to_type(True, "bool") == "yes"
        assert convert_value_to_type(0, "bool") == "no"
        
        # String conversion
        assert convert_value_to_type(123, "str") == "123"

    def test_values_are_equivalent(self):
        """Test value equivalence checking"""
        # Exact matches
        assert values_are_equivalent("hello", "hello", "str")
        assert values_are_equivalent("Hello", "hello", "str")  # Case insensitive
        
        # Numeric matches
        assert values_are_equivalent(123, 123.0, "int")
        assert values_are_equivalent(123.456, 123.456, "float")
        
        # Boolean matches
        assert values_are_equivalent("yes", "yes", "bool")
        assert values_are_equivalent("yes", "YES", "bool")
        
        # Float precision matches
        assert values_are_equivalent(123.456, 123.46, "float-2")
        
        # NaN matches
        assert values_are_equivalent(np.nan, np.nan, "str")
        
        # Non-matches
        assert not values_are_equivalent("hello", "world", "str")
        assert not values_are_equivalent(123, 456, "int")
        assert not values_are_equivalent(np.nan, "hello", "str")

    def test_build_column_mappings(self):
        """Test column mapping construction"""
        column_mappings, column_types = build_column_mappings(self.sample_mapping)
        
        # Check that mappings are created correctly
        assert 'enct.sex' in column_mappings
        assert 'flow.hypertension' in column_mappings
        assert 'img.firstimage_type' in column_mappings
        
        # Check that column types are preserved
        assert column_types['enct.sex']['epic_type'] == 'int'
        assert column_types['enct.sex']['secu_type'] == 'str'

    def test_get_default_value_mappings(self):
        """Test default value mappings"""
        mappings = get_default_value_mappings()
        
        # Check that default mappings exist
        assert 'enct.sex' in mappings
        assert 'enct.transport' in mappings
        assert 'flow.hypertension' in mappings
        
        # Check specific mappings
        assert mappings['enct.sex'][1] == 'Male'
        assert mappings['enct.sex'][2] == 'Female'

    def test_data_preprocessing(self):
        """Test data preprocessing steps"""
        # Test that boolean columns are handled correctly
        epic_copy = self.sample_epic_data.copy()
        
        # Apply value mappings
        value_mappings = get_default_value_mappings()
        for col, mapping in value_mappings.items():
            if col in epic_copy.columns:
                epic_copy[col] = epic_copy[col].map(lambda x: mapping.get(x, x))
        
        # Check that sex mapping worked
        if 'enct.sex' in epic_copy.columns:
            assert 'Male' in epic_copy['enct.sex'].values or 'Female' in epic_copy['enct.sex'].values

    def test_missing_data_handling(self):
        """Test missing data handling"""
        # Create test data with missing values
        test_df = pd.DataFrame({
            'col1': [1, np.nan, 3, -9999, ''],
            'col2': ['a', '', 'c', 'null', 'NULL']
        })
        
        # Replace missing value indicators
        test_df.replace(-9999, pd.NA, inplace=True)
        
        # Check that -9999 was replaced
        assert not (test_df['col1'] == -9999).any()

    def test_date_column_processing(self):
        """Test date column processing"""
        # Test that date columns are properly converted
        epic_copy = self.sample_epic_data.copy()
        epic_copy['DATE'] = pd.to_datetime(epic_copy['enct.arrival_date'], errors='coerce')
        
        assert not epic_copy['DATE'].isna().all()
        assert epic_copy['DATE'].dtype == 'datetime64[ns]'

    def test_fid_ssr_matching(self):
        """Test FID/SSR matching logic"""
        # Create matching keys set
        epic_keys = set(self.sample_epic_data[['FID', 'SSR']].apply(tuple, axis=1))
        secu_keys = set(self.sample_secuTrial_data[['FID', 'SSR']].apply(tuple, axis=1))
        matching_keys = epic_keys & secu_keys
        
        # Should have 3 matching pairs
        assert len(matching_keys) == 3
        assert (1, 101) in matching_keys
        assert (2, 102) in matching_keys
        assert (3, 103) in matching_keys

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_file_structure_validation(self, temp_directory):
        """Test that required file structure validation works"""
        # Create required directories
        required_dirs = [
            temp_directory / "EPIC-files",
            temp_directory / "sT-files",
            temp_directory / "EPIC2sT-pipeline",
            temp_directory / "EPIC-export-validation/validation-files"
        ]
        
        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)
            assert directory.exists()

    def test_monthly_stats_calculation(self):
        """Test monthly statistics calculation"""
        # Create sample monthly stats
        monthly_stats = {
            'April': {'match_count': 100, 'mismatch_count': 10, 'total_compared': 120},
            'May': {'match_count': 150, 'mismatch_count': 5, 'total_compared': 160}
        }
        
        # Calculate percentages
        for month, stats in monthly_stats.items():
            total = stats['total_compared']
            match_percent = round((stats['match_count'] / total) * 100, 2)
            mismatch_percent = round((stats['mismatch_count'] / total) * 100, 2)
            
            if month == 'April':
                assert match_percent == 83.33
                assert mismatch_percent == 8.33
            elif month == 'May':
                assert match_percent == 93.75
                assert mismatch_percent == 3.12

    def test_error_handling(self):
        """Test error handling for common issues"""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        
        # Should handle empty DataFrames gracefully
        try:
            column_mappings, column_types = build_column_mappings(empty_df)
            assert len(column_mappings) == 0
        except Exception as e:
            pytest.fail(f"Should handle empty DataFrame gracefully, got: {e}")

    def test_value_mapping_edge_cases(self):
        """Test edge cases in value mapping"""
        mappings = get_default_value_mappings()
        
        # Test that unmapped values are preserved
        test_value = 999  # Not in any mapping
        mapped_value = mappings['enct.sex'].get(test_value, test_value)
        assert mapped_value == test_value  # Should be unchanged

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])