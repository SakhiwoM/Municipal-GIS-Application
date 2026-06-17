import pandas as pd

from .spatial_utils import normalize_column_names

def process_valuation_csv(file_path):
    """
    Reads a tabular valuation roll dataset and converts it into a pandas DataFrame.
    Empty or missing fields can be handled during or after serialization.
    """
    try:
        # Read the tabular CSV dataset
        df = pd.read_csv(file_path)
        
        # Normalize column headers to keep consistency across the app
        df = normalize_column_names(df)
        
        return df

    except Exception as e:
        raise RuntimeError(f"Error reading valuation roll tabular array: {str(e)}")