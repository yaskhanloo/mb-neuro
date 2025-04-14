# This file would contain the comparison functions from your notebook
# I'll include a modified version of one of your comparison functions as an example

import pandas as pd
import re
from datetime import datetime
from io import StringIO

def compare_epic_secuTrial(epic_df, secuTrial_df, mapping_df, value_mappings=None):
    """
    Compares values and data types between EPIC and secuTrial DataFrames using a mapping file,
    accounting for data type differences properly. Includes monthly breakdown of statistics
    and variable-level statistics.
    
    Returns:
        DataFrame: DataFrame with mismatched results in values and data types.
        dict: Dictionary containing percentage statistics.
        dict: Dictionary containing monthly statistics.
        dict: Dictionary containing variable-level statistics.
    """
    # Implementation from your notebook
    # ...

def generate_comparison_report(mismatched_results, overall_stats, monthly_stats, variable_stats):
    """
    Generates a comprehensive report from the comparison results
    
    Args:
        mismatched_results (DataFrame): DataFrame with details of mismatched values
        overall_stats (dict): Dictionary with overall statistics
        monthly_stats (dict): Dictionary with monthly breakdown of statistics
        variable_stats (dict): Dictionary with variable-level statistics
        
    Returns:
        str: Markdown formatted report
    """
    # Implementation from your notebook
    # ...

def get_top_problematic_variables(variable_stats, sort_by='mismatch_percent', top_n=10):
    """
    Identify the most problematic variables based on specified criteria
    
    Args:
        variable_stats (dict): Dictionary containing variable-level statistics
        sort_by (str): Criteria to sort by: 'mismatch_percent', 'missing_epic_percent', 
                       'missing_secuTrial_percent', or 'total_problems'
        top_n (int): Number of variables to return
        
    Returns:
        DataFrame: Top problematic variables sorted by the specified criteria
    """
    # Implementation from your notebook
    # ...