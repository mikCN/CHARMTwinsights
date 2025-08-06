import logging
import joblib # Keep for general saving/loading, but MLflow will manage models
import pandas as pd
import numpy as np
import os # For creating directories for saving
import inspect
import pickle
from datetime import datetime
from sklearn.model_selection import train_test_split 
# --- MLflow Imports ---
import mlflow
import mlflow.pyfunc
# --- Lifelines Imports for Cox PH ---
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index # For explicit C-index calculation
import joblib
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Use logger instead of direct logging.info
# Assume dataloader and preprocessing are adjusted to provide necessary columns
from twinsight_model import dataloader_cox
from twinsight_model import preprocessing_cox
# Import specific functions/classes directly from sibling modules
from .dataloader_cox import load_configuration, load_data_from_bigquery 
from .preprocessing_cox import split_data, create_preprocessor, apply_preprocessing 
from .utils import check_for_data 
# --- Logging Setup ---
# Configure logging only once for the module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# --- Helper Function for Model Evaluation ---
# This is the single, corrected version of evaluate_cox_model.
def evaluate_cox_model(model, X_test, y_test_duration, y_test_event, duration_col, event_col):
    """
    Evaluates the Cox PH model on the test set.

    Args:
        model: The trained CoxPHFitter model.
        X_test (pd.DataFrame): Test features.
        y_test_duration (pd.Series): Test durations.
        y_test_event (pd.Series): Test event indicators.
        duration_col (str): Name of the duration column in the original DataFrame.
        event_col (str): Name of the event column in the original DataFrame.

    Returns:
        dict: A dictionary of evaluation metrics.
    """
    logger.info(f"Type of model in evaluate_cox_model: {type(model)}")
    evaluation_metrics = {}
    try:
        # Create a combined DataFrame for scoring as expected by model.score()
        test_df_for_score = X_test.copy()
        test_df_for_score[duration_col] = y_test_duration
        test_df_for_score[event_col] = y_test_event

        if hasattr(model, 'score'):
            logger.info(f"Model has score method. Signature: {inspect.signature(model.score)}")
            # Use model.score with the combined DataFrame. It typically returns average partial log-likelihood.
            log_likelihood_score = model.score(test_df_for_score)
            
            # For explicit Concordance Index calculation, use lifelines.utils.concordance_index
            predictions_for_cindex = model.predict_partial_hazard(X_test)
            c_index_explicit = concordance_index(y_test_duration, predictions_for_cindex, y_test_event)

            evaluation_metrics['log_likelihood_score'] = log_likelihood_score
            evaluation_metrics['c_index'] = c_index_explicit
            logger.info(f"Log-likelihood Score: {log_likelihood_score}")
            logger.info(f"Concordance Index (C-index): {c_index_explicit}")

        else:
            logger.info("Model does NOT have a score method!")
            evaluation_metrics['c_index'] = np.nan # Indicate not calculated if score method is missing

    except Exception as e:
        logger.error(f"Error during model evaluation: {e}", exc_info=True)
        # evaluation_metrics will remain empty or partial if error occurs
    return evaluation_metrics
def split_time_to_event_data(X, y_duration, y_event, test_size=0.2, random_state=None):
    """
    Splits time-to-event data into training and testing sets.
    Ensures that duration and event status are split together with features.

    Args:
        X (pd.DataFrame): Feature DataFrame.
        y_duration (pd.Series): Series of event/censoring durations.
        y_event (pd.Series): Series of event indicators (1=event, 0=censored).
        test_size (float): Proportion of the dataset to include in the test split.
        random_state (int): Random seed for reproducibility.

    Returns:
        tuple: (X_train, X_test, y_train_duration, y_test_duration, y_train_event, y_test_event)
    """
    logger.info("Starting data splitting for time-to-event data...")

    # Combine y_duration and y_event for a consistent split, then separate
    y_combined = np.stack([y_duration, y_event], axis=1)

    X_train, X_test, y_combined_train, y_combined_test = train_test_split(
        X, y_combined, test_size=test_size, random_state=random_state
    )

    # Re-separate y_duration and y_event, ensuring Series names and indices are preserved
    y_train_duration = pd.Series(y_combined_train[:, 0], index=X_train.index, name=y_duration.name)
    y_train_event = pd.Series(y_combined_train[:, 1], index=X_train.index, name=y_event.name)
    y_test_duration = pd.Series(y_combined_test[:, 0], index=X_test.index, name=y_duration.name)
    y_test_event = pd.Series(y_combined_test[:, 1], index=X_test.index, name=y_event.name)

    logger.info("Data splitting for time-to-event data complete.")
    return X_train, X_test, y_train_duration, y_test_duration, y_train_event, y_test_event
# --- MLflow Model Wrapper for CoxPHFitter (Retained for structure, but not used for pickling anymore) ---
# This class was previously used for mlflow.pyfunc.log_model, but we are now using direct pickling.
# It is kept here as it defines the structure of a custom pyfunc model wrapper.
class LifelinesCoxPHWrapper(mlflow.pyfunc.PythonModel):
    def __init__(self, duration_col, event_col, feature_names):
        self._duration_col = duration_col
        self._event_col = event_col
        self._feature_names = feature_names

    def load_context(self, context):
        self.model = joblib.load(context.artifacts["model"])
        self.preprocessor = joblib.load(context.artifacts["preprocessor"])
        self.duration_col = self._duration_col
        self.event_col = self._event_col
        self.feature_names = self._feature_names
        logger.info("LifelinesCoxPHWrapper loaded successfully.")

    def predict(self, context, model_input):
        if not isinstance(model_input, pd.DataFrame):
            raise TypeError("Input to predict must be a pandas DataFrame.")
        
        if self.feature_names:
            model_input = model_input.reindex(columns=self.feature_names, fill_value=0.0)

        return self.model.predict_partial_hazard(model_input)

    def predict_survival_function_wrapper(self, model_input, times):
        if not isinstance(model_input, pd.DataFrame):
            raise TypeError("Input to predict_survival_function_wrapper must be a pandas DataFrame.")

        if self.feature_names:
            model_input = model_input.reindex(columns=self.feature_names, fill_value=0.0)
            
        return self.model.predict_survival_function(model_input, times=times)
# --- Helper functions for joblib saving/loading (not used by run_end_to_end_pipeline directly now) ---
def save_model_joblib(model, path):
    """
    Save the trained model to a file using joblib.
    """
    try:
        joblib.dump(model, path)
        logger.info(f"Model saved to {path}")
    except Exception as e:
        logger.error(f"Failed to save model: {e}")
        raise
def load_model_joblib(path):
    """
    Load a model from a file using joblib.
    """
    try:
        model = joblib.load(path)
        logger.info(f"Model loaded from {path}")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
# --- Main End-to-End Pipeline Function ---
def run_end_to_end_pipeline(config_path, preloaded_data_df=None, test_size=0.2, random_state=42, **model_kwargs):
    """
    Runs the end-to-end ML pipeline for the Cox Proportional Hazards model.

    Args:
        config_path (str): Path to the configuration YAML file.
        preloaded_data_df (pd.DataFrame, optional): Preloaded data DataFrame. If None, data is loaded from BigQuery.
        test_size (float, optional): Proportion of the dataset to include in the test split. Defaults to 0.2.
        random_state (int, optional): Random seed for reproducibility. Defaults to 42.
        **model_kwargs: Keyword arguments for CoxPHFitter initialization (e.g., penalizer, l1_ratio).

    Returns:
        tuple: A tuple containing the trained CoxPHFitter model object and evaluation metrics.
    """
    logger.info("Starting the end-to-end ML pipeline for Cox PH model...")

    # MLflow run for tracking parameters and metrics (not for model artifact logging via pyfunc)
    with mlflow.start_run() as run:
        mlflow_run_id = run.info.run_id
        logger.info(f"MLflow Run ID: {mlflow_run_id}")

        mlflow.log_params(model_kwargs)
        logger.info(f"Logged model parameters: {model_kwargs}")

        config = dataloader_cox.load_configuration(config_path)
        logger.info("Configuration loaded successfully.")

        data_df = preloaded_data_df if preloaded_data_df is not None else dataloader_cox.load_data_from_bigquery(config)
        logger.info(f"Using preloaded data. Shape: {data_df.shape}")

        # Identify features and target columns from config
        feature_columns = config["model_features_final"]
        duration_col = config["model_io_columns"]["duration_col"]
        event_col = config["model_io_columns"]["event_col"]
        
        logger.info(f"Identified {len(feature_columns)} predictor features.")
        logger.info(f"Feature columns: {feature_columns}")

        # Prepare X, y, event, duration for splitting
        X = data_df[feature_columns].copy()
        y_duration = data_df[duration_col]
        y_event = data_df[event_col]

        logger.info("Splitting data into training and testing sets...")

        X_train_raw, X_test_raw, y_train_duration, y_test_duration, y_train_event, y_test_event = \
        split_time_to_event_data(X, y_duration, y_event, test_size, random_state) # <--- CHANGED THIS LINE
        
        logger.info(f"Data split complete: {len(X_train_raw)} train samples, {len(X_test_raw)} test samples.")
        logger.info(f"Raw data split. X_train_raw shape: {X_train_raw.shape}, X_test_raw shape: {X_test_raw.shape}")

        # Convert relevant columns to float64 for preprocessing consistency
        for col in X_train_raw.select_dtypes(include=['Int64', 'boolean']).columns:
            X_train_raw[col] = X_train_raw[col].astype(float)
        for col in X_test_raw.select_dtypes(include=['Int64', 'boolean']).columns:
            X_test_raw[col] = X_test_raw[col].astype(float)


        logger.info("Applying feature preprocessing pipeline...")
        # Create and fit preprocessor on training data
        fitted_preprocessor = preprocessing_cox.create_preprocessor(X_train_raw)
        
        logger.info("Feature preprocessing pipeline created and fitted.")

        # Apply preprocessing
        X_train_processed_array, X_test_processed_array = preprocessing_cox.apply_preprocessing(
            fitted_preprocessor, X_train_raw, X_test_raw
        )
        
        # Get processed feature names
        feature_columns_processed = fitted_preprocessor.get_feature_names_out().tolist()

        # Convert processed arrays back to DataFrame with correct column names
        X_train_processed = pd.DataFrame(X_train_processed_array, columns=feature_columns_processed)
        X_test_processed = pd.DataFrame(X_test_processed_array, columns=feature_columns_processed)

        logger.info(f"Processed X_train shape: {X_train_processed.shape}, dtypes: {X_train_processed.dtypes.to_dict()}")
        logger.info(f"Processed X_test shape: {X_test_processed.shape}, dtype: {X_test_processed.dtypes.to_dict()}")
        logger.info(f"Features processed. X_train_processed shape: {X_train_processed.shape}, X_test_processed shape: {X_test_processed.shape}")
        
        logger.info("Checking processed features for potential convergence issues before model fit...")
        # Placeholder for dynamic feature dropping logic if needed
        logger.info("No additional problematic processed columns identified for temporary drop.")
        logger.info(f"Final features for model fit. X_train shape: {X_train_processed.shape}, X_test shape: {X_test_processed.shape}")


        logger.info("Training the Cox Proportional Hazards model...")
        logger.info("Initializing CoxPHFitter model...")
        trained_cox_model = CoxPHFitter(**model_kwargs)
        
        # Combine data into a single DataFrame for fitting (robust method)
        df_train_combined = X_train_processed.copy()
        df_train_combined[duration_col] = y_train_duration
        df_train_combined[event_col] = y_train_event
        trained_cox_model.fit(df_train_combined, duration_col=duration_col, event_col=event_col)
        
        logger.info("Model training completed.")
        logger.info("Cox PH Model training completed successfully.")

        logger.info("\n--- Cox PH Model Summary ---")
        trained_cox_model.print_summary() # Prints to stdout
        logger.info("----------------------------")

        logger.info("Evaluating the Cox PH model on the test set...")
        evaluation_metrics = evaluate_cox_model(
            trained_cox_model, X_test_processed, y_test_duration, y_test_event, duration_col, event_col
        )
        mlflow.log_metrics(evaluation_metrics) # Log metrics to MLflow

        # --- Pickle the trained model and preprocessor directly ---
        pickled_models_output_dir = "/home/jupyter/Cox_package/regression_model/pickled_models"
        os.makedirs(pickled_models_output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"cox_ph_model_{timestamp}.pkl"
        preprocessor_filename = f"preprocessor_{timestamp}.pkl"

        pickled_model_path = os.path.join(pickled_models_output_dir, model_filename)
        pickled_preprocessor_path = os.path.join(pickled_models_output_dir, preprocessor_filename)

        try:
            with open(pickled_model_path, 'wb') as f:
                pickle.dump(trained_cox_model, f)
            logger.info(f"Cox PH model pickled successfully to: {pickled_model_path}")

            with open(pickled_preprocessor_path, 'wb') as f:
                pickle.dump(fitted_preprocessor, f)
            logger.info(f"Preprocessor pickled successfully to: {pickled_preprocessor_path}")
            
            # Log the paths of the pickled files as MLflow artifacts
            mlflow.log_artifact(pickled_model_path, "pickled_model")
            mlflow.log_artifact(pickled_preprocessor_path, "pickled_preprocessor")

        except Exception as e:
            logger.error(f"Error pickling model or preprocessor: {e}", exc_info=True)
            raise # Re-raise to signal pipeline failure if pickling fails

        logger.info("ML pipeline completed successfully (with potential warnings/errors).")
        logger.info("\n--- Pipeline Execution Summary ---")
        logger.info(f"Trained Cox PH Model Object: {trained_cox_model}")
        logger.info(f"Final Evaluation Metrics: {evaluation_metrics}")
        logger.info(f"Cox PH Model pickled to: {pickled_model_path}")
        logger.info(f"Preprocessor pickled to: {pickled_preprocessor_path}")
        logger.info(f"Check your MLflow UI (if running) for run details and logged artifact paths.")

    return trained_cox_model, evaluation_metrics, pickled_model_path, pickled_preprocessor_path
# --- Standalone Execution Block for Direct Testing ---
# This block runs only when model_cox.py is executed directly (e.g., `python model_cox.py`)
if __name__ == "__main__":
    _config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configuration_cox.yaml') # Corrected path
    _model_kwargs = {
        "penalizer": 0.001,
        "l1_ratio": 0.0,
    }

    # IMPORTANT: For this __main__ block to run with actual data, you must remove/comment out
    # the MockDataloader and MockPreprocessing sections below and ensure
    # dataloader_cox.load_data_from_bigquery works in this context.
    
    # --- Mocks for Standalone Testing (COMMENT OUT FOR REAL DATA) ---
    # These mocks are used when running model.py directly for quick testing without BigQuery access.
    # If you want to test the full pipeline from __main__ with real BigQuery data,
    # you MUST comment out these mock assignments.

    # Restore original functions needed here in case they were mocked out elsewhere before
    # For testing from __main__
    _original_dataloader_load_config = dataloader_cox.load_configuration
    _original_dataloader_load_data = dataloader_cox.load_data_from_bigquery
    _original_dataloader_split_data = dataloader_cox.split_time_to_event_data # Keep original split function
    _original_preprocessing_create_preprocessor = preprocessing_cox.create_preprocessor
    _original_preprocessing_apply_preprocessing = preprocessing_cox.apply_preprocessing


    class MockDataloader:
        @staticmethod
        def load_configuration(path):
            return {
                'outcome': {'name': 'copd_status'},
                'model_io_columns': {'duration_col': 'time_to_event_days', 'event_col': 'event_observed'},
                'model_features_final': ['age_at_time_0', 'smoking_status', 'bmi', 'diabetes', 'cardiovascular_disease', 'ethnicity', 'sex_at_birth', 'alcohol_use'],
                'co_indicators': [{'name': 'obesity', 'domain': 'condition_occurrence', 'concepts_include': [433736]}],
                'features': [{'name': 'smoking_status', 'domain': 'observation', 'type': 'categorical'}, {'name': 'bmi', 'domain': 'measurement', 'type': 'continuous'}, {'name': 'age_at_time_0', 'domain': 'person', 'type': 'continuous'}]
            }

        @staticmethod
        def load_data_from_bigquery(config):
            np.random.seed(42)
            n_samples = 1000
            
            data = {
                'person_id': range(n_samples),
                'age_at_time_0': np.random.randint(40, 80, n_samples).astype(float),
                'smoking_status': np.random.choice([0, 1, np.nan], n_samples, p=[0.4, 0.4, 0.2]), # Include NaNs for smoking_status
                'bmi': np.random.normal(28, 5, n_samples).astype(float),
                'diabetes': np.random.choice([0, 1], n_samples, p=[0.8, 0.2]).astype(float),
                'cardiovascular_disease': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]).astype(float),
                'ethnicity': np.random.choice(['Not Hispanic or Latino', 'Hispanic or Latino'], n_samples),
                'sex_at_birth': np.random.choice(['Male', 'Female'], n_samples),
                'obesity': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]).astype(float),
                'alcohol_use': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]).astype(float),
                'time_to_event_days': np.random.exponential(365 * 3, n_samples).astype(float),
                'event_observed': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]).astype(float),
            }
            df = pd.DataFrame(data)

            df['ethnicity'] = df['ethnicity'].astype('category')
            df['sex_at_birth'] = df['sex_at_birth'].astype('category')
            df['smoking_status'] = df['smoking_status'].astype('category') # If smoking is categorical

            return df

        @staticmethod
        def split_time_to_event_data(X, y_duration, y_event, test_size=0.2, random_state=None):
            from sklearn.model_selection import train_test_split
            y_combined = np.stack([y_duration, y_event], axis=1)
            X_train, X_test, y_combined_train, y_combined_test = train_test_split(
                X, y_combined, test_size=test_size, random_state=random_state
            )
            y_train_duration = pd.Series(y_combined_train[:, 0], index=X_train.index, name=y_duration.name)
            y_train_event = pd.Series(y_combined_train[:, 1], index=X_train.index, name=y_event.name)
            y_test_duration = pd.Series(y_combined_test[:, 0], index=X_test.index, name=y_duration.name)
            y_test_event = pd.Series(y_combined_test[:, 1], index=X_test.index, name=y_event.name)
            return X_train, X_test, y_train_duration, y_test_duration, y_train_event, y_test_event


    class MockPreprocessor:
        def __init__(self):
            self.feature_names_out_ = None
        def fit(self, X):
            self.feature_names_out_ = ['num__' + col for col in X.select_dtypes(include=np.number).columns if col not in ['person_id', 'time_to_event_days', 'event_observed']] + \
                                      ['cat__' + col + '_' + str(val) for col in X.select_dtypes(include='category').columns for val in X[col].unique()]
            return self
        def transform(self, X):
            transformed_df = pd.DataFrame()
            for col in X.columns:
                if pd.api.types.is_numeric_dtype(X[col]):
                    if col not in ['person_id', 'time_to_event_days', 'event_observed']: # Exclude non-feature numerics
                        transformed_df['num__' + col] = X[col].astype(float)
                elif pd.api.types.is_categorical_dtype(X[col]) or pd.api.types.is_object_dtype(X[col]):
                    dummies = pd.get_dummies(X[col], prefix='cat__' + col, dtype=float)
                    transformed_df = pd.concat([transformed_df, dummies], axis=1)
                else:
                    transformed_df[col] = X[col]
            
            return transformed_df.reindex(columns=self.feature_names_out_, fill_value=0.0).values

        def get_feature_names_out(self):
            return self.feature_names_out_


    # Assign mocks for standalone execution
    dataloader_cox.load_configuration = MockDataloader.load_configuration
    dataloader_cox.load_data_from_bigquery = MockDataloader.load_data_from_bigquery
    dataloader_cox.split_time_to_event_data = MockDataloader.split_time_to_event_data

    preprocessing_cox.create_preprocessor = MockPreprocessor.create_preprocessor
    preprocessing_cox.apply_preprocessing = MockPreprocessor.apply_preprocessing

    # --- End Mocks ---

    try:
        logging.info("Starting direct model.py execution...")
        run_end_to_end_pipeline(
            config_path=_config_path,
            test_size=0.2,
            random_state=42,
            **_model_kwargs
        )
        logging.info("Direct model.py execution completed successfully.")
    except Exception as e:
        logging.error(f"Direct model.py execution failed: {e}", exc_info=True)
    finally:
        # Restore original functions after execution, ensuring proper cleanup
        dataloader_cox.load_configuration = _original_dataloader_load_config
        dataloader_cox.load_data_from_bigquery = _original_dataloader_load_data
        dataloader_cox.split_time_to_event_data = _original_dataloader_split_data
        preprocessing_cox.create_preprocessor = _original_preprocessing_create_preprocessor
        preprocessing_cox.apply_preprocessing = _original_preprocessing_apply_preprocessing