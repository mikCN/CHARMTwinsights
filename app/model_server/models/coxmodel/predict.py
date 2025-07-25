#!/usr/bin/env python3
import sys
import json
import pandas as pd
import numpy as np
import pickle
from lifelines import CoxPHFitter
from sklearn.compose import ColumnTransformer # Keep if your preprocessor uses ColumnTransformer explicitly


# --- CONFIGURE THESE PATHS ---
# ADJUST THESE FILENAMES AND PATHS TO MATCH YOUR EXACT .PKL FILES AND THEIR LOCATION!
# Using the latest timestamp from your successful run
MODEL_PATH = "pickled_models/cox_ph_model_20250724_170001.pkl" # <--- UPDATED FILENAME
PREPROCESSOR_PATH = "pickled_models/preprocessor_20250724_170001.pkl" # <--- UPDATED FILENAME


# Global variables to hold the loaded model and preprocessor
_loaded_cox_model = None
_loaded_preprocessor = None
_loaded_feature_names = None # Names of features AFTER preprocessing

def _load_artifacts():
    """Internal function to load the model and preprocessor on first use."""
    global _loaded_cox_model, _loaded_preprocessor, _loaded_feature_names
    if _loaded_cox_model is None or _loaded_preprocessor is None:
        try:
            with open(MODEL_PATH, 'rb') as f:
                _loaded_cox_model = pickle.load(f)
            with open(PREPROCESSOR_PATH, 'rb') as f:
                _loaded_preprocessor = pickle.load(f)
            _loaded_feature_names = _loaded_preprocessor.get_feature_names_out().tolist()
            print("Model and preprocessor loaded successfully.", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: Model or preprocessor file not found. Check paths: {MODEL_PATH}, {PREPROCESSOR_PATH}", file=sys.stderr)
            sys.exit(1) # Exit if files are missing
        except Exception as e:
            print(f"Error loading model or preprocessor: {e}", file=sys.stderr)
            sys.exit(1) # Exit on other loading errors

def get_prediction_for_single_record(record_dict: dict) -> dict:
    """
    Performs prediction for a single input record (dictionary).
    This function handles preprocessing and prediction for one individual.

    Args:
        record_dict (dict): A dictionary representing a single input record.

    Returns:
        dict: A dictionary containing prediction results (e.g., partial hazard,
              survival probabilities) for this single record.
    """
    _load_artifacts() # Ensure model and preprocessor are loaded

    # Convert the single record dict to a single-row DataFrame
    input_df_raw = pd.DataFrame([record_dict]).copy()

    # 1. Prepare raw input data for preprocessing
    # This list MUST match the exact raw feature columns your preprocessor expects
    expected_raw_features = [
        'ethnicity', 'sex_at_birth', 'obesity', 'diabetes',
        'cardiovascular_disease', 'smoking_status', 'alcohol_use',
        'bmi', 'age_at_time_0'
        # Add 'person_id' here if it's meant to be processed by preprocessor or just passed through
    ]

    # Reindex to ensure all expected features are present, fill missing with NaN
    X_predict_raw = input_df_raw.reindex(columns=expected_raw_features, fill_value=np.nan).copy()

    # Ensure numeric columns are float (including Int64 and boolean if they exist in raw data)
    for col in X_predict_raw.select_dtypes(include=['int64', 'Int64', 'boolean']).columns:
        X_predict_raw[col] = X_predict_raw[col].astype(float)
    
    # Ensure categorical/object columns are 'category' dtype if that's what your preprocessor expects
    # (assuming they are strings at this point)
    for col in X_predict_raw.select_dtypes(include=['object']).columns:
        X_predict_raw[col] = X_predict_raw[col].astype('category')
    
    # 2. Apply preprocessing (preprocessor is already fitted from _load_artifacts)
    # _loaded_preprocessor.transform returns a NumPy array.
    processed_array = _loaded_preprocessor.transform(X_predict_raw)
    
    # Convert processed array back to DataFrame with correct column names and original index
    processed_df = pd.DataFrame(processed_array, columns=_loaded_feature_names, index=X_predict_raw.index)

    # 3. Make predictions
    partial_hazards = _loaded_cox_model.predict_partial_hazard(processed_df)
    survival_at_5_years = _loaded_cox_model.predict_survival_function(processed_df, times=[1825])

    # Extract the single result and handle np.nan values for JSON compatibility
    partial_hazard_val = partial_hazards.iloc[0]
    survival_prob_val = survival_at_5_years.loc[1825.0].iloc[0]

    result_dict = {
        'partial_hazard': None if pd.isna(partial_hazard_val) else partial_hazard_val, # <--- CORRECTED FOR JSON
        'survival_probability_5_years': None if pd.isna(survival_prob_val) else survival_prob_val # <--- CORRECTED FOR JSON
    }

    # If 'person_id' was in the original input and you want it in the output
    if 'person_id' in record_dict:
        result_dict['person_id'] = record_dict['person_id']

    return result_dict


def main():
    # Adheres to the original script's command-line interface: predict.py <input.json>
    if len(sys.argv) != 2:
        print("Usage: predict.py <input.json>", file=sys.stderr)
        sys.exit(1)
    
    input_file_path = sys.argv[1]

    # Load input records from the JSON file
    try:
        with open(input_file_path, 'r') as f:
            X_raw_records = json.load(f) 
        
        # --- IMPROVED INPUT HANDLING ---
        # If input is a single dictionary, wrap it in a list for consistent processing
        if isinstance(X_raw_records, dict):
            X_raw_records = [X_raw_records]
        # Ensure X_raw_records is indeed a list of dictionaries
        elif not isinstance(X_raw_records, list) or not all(isinstance(item, dict) for item in X_raw_records):
            raise ValueError("Input JSON must be a dictionary or a list of dictionaries.")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file_path}. Is it valid JSON?", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        print(f"Error in input data format: {ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading or parsing input data: {e}", file=sys.stderr)
        sys.exit(1)

    res = [] # List to accumulate results for each record
    # Iterate over each record in the input list, process it, and append its result
    for x_record_dict in X_raw_records:
        try:
            yhat_record = get_prediction_for_single_record(x_record_dict)
            res.append(yhat_record) # Append the dictionary result for the current record
            
        except Exception as e:
            # Handle prediction errors for individual records gracefully,
            # or re-raise if you want pipeline to fail on first error.
            print(f"Warning: Error processing record {x_record_dict.get('person_id', 'unknown')}: {e}", file=sys.stderr)
            res.append({"error": str(e), "original_input": x_record_dict})


    # Print the final JSON output to stdout
    print(json.dumps(res, indent=2)) # Use indent=2 for readable output
        
if __name__ == "__main__":
    main()