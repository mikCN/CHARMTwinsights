import logging
from typing import Tuple, Optional, Union
import pandas as pd
import numpy as np 
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Use logger for consistency
class OutlierCapper(BaseEstimator, TransformerMixin):
    def __init__(self, lower_bound_quantile=None, upper_bound_quantile=None):
        # Store the quantile parameters
        self.lower_bound_quantile = lower_bound_quantile
        self.upper_bound_quantile = upper_bound_quantile

        # These will store the *calculated* bounds after fitting
        self.lower_bound_values = {}
        self.upper_bound_values = {}

    def fit(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            # Convert to DataFrame if it's a Series or array for consistent handling
            X = pd.DataFrame(X)

        for col in X.columns:
            # Only calculate for numerical columns and if quantiles are specified
            if pd.api.types.is_numeric_dtype(X[col]) and self.lower_bound_quantile is not None and self.upper_bound_quantile is not None:
                # Calculate bounds based on quantiles
                self.lower_bound_values[col] = X[col].quantile(self.lower_bound_quantile)
                self.upper_bound_values[col] = X[col].quantile(self.upper_bound_quantile)
            else:
                # If no quantiles, or not numeric, don't cap
                self.lower_bound_values[col] = None
                self.upper_bound_values[col] = None
        return self

    def transform(self, X):
        if not isinstance(X, pd.DataFrame):
            X_transformed = pd.DataFrame(X, columns=[X.name]) if isinstance(X, pd.Series) else pd.DataFrame(X)
        else:
            X_transformed = X.copy()

        for col in X_transformed.columns:
            if col in self.lower_bound_values and self.lower_bound_values[col] is not None:
                X_transformed[col] = X_transformed[col].clip(
                    self.lower_bound_values[col],
                    self.upper_bound_values[col]
                )
        return X_transformed

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            if hasattr(self, '_feature_names_in'): # If you store input names from fit
                return self._feature_names_in
            return list(self.lower_bound_values.keys()) # Or based on fitted columns
        return list(input_features) # Assume output features are same as input
def split_data(
    df: pd.DataFrame,
    duration_column: str,
    event_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify_by: Optional[pd.Series] = None
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.Series, pd.Series]:
    """
    Splits the dataset into training and testing sets, explicitly separating features (X),
    duration, and event status for time-to-event modeling.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing features, duration, and event.
        duration_column (str): The name of the column containing time to event/censoring.
        event_column (str): The name of the column indicating event occurrence (1) or censoring (0).
        test_size (float): Proportion of the dataset to include in the test split. Default is 0.2.
        random_state (int): Random seed for reproducibility. Default is 42.
        stratify_by (pd.Series or None): If not None, data is split in a stratified fashion based on this variable.
                                         Typically, this would be the event_column to ensure similar event rates.

    Returns:
        Tuple: (X_train, duration_train, event_train, X_test, duration_test, event_test)
               where X are DataFrames and duration/event are Series.

    Raises:
        KeyError: If duration_column or event_column are not in df.
        ValueError: If df is empty or has insufficient rows for splitting.
        TypeError: If input df is not a pandas DataFrame.
    """
    logger.info("Starting data splitting for time-to-event data...")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input df must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("The input DataFrame is empty.")

    if duration_column not in df.columns:
        raise KeyError(f"Duration column '{duration_column}' does not exist in the DataFrame.")
    if event_column not in df.columns:
        raise KeyError(f"Event column '{event_column}' does not exist in the DataFrame.")

    if test_size <= 0 or test_size >= 1:
        raise ValueError("test_size must be between 0 and 1 (exclusive).")

    if len(df) < 2:
        raise ValueError("DataFrame must have at least 2 rows to split.")

    # Separate features (X), duration, and event status (y)
    # The dataframe passed to this function from model.py should already contain
    # only the feature columns + duration_column + event_column.
    X = df.drop(columns=[duration_column, event_column])
    duration = df[duration_column]
    event = df[event_column]

    # Optional: Check for missing values and log warnings in features
    if X.isnull().any().any():
        logger.warning("There are missing values in the features (X) *before* splitting. Consider handling them.")
    if duration.isnull().any():
        logger.warning("There are missing values in the duration column *before* splitting. This will cause issues for lifelines.")
    if event.isnull().any():
        logger.warning("There are missing values in the event column *before* splitting. This will cause issues for lifelines.")

    try:
        # Perform the split on X, duration, and event simultaneously to keep rows aligned
        X_train, X_test, duration_train, duration_test, event_train, event_test = train_test_split(
            X, duration, event, test_size=test_size, random_state=random_state, stratify=stratify_by
        )
    except ValueError as e:
        logger.error(f"Error during train/test split: {e}")
        raise

    logger.info(
        f"Data split complete: {len(X_train)} train samples, {len(X_test)} test samples."
    )
    # Return features as DataFrames and duration/event as Series
    return X_train, duration_train, event_train, X_test, duration_test, event_test
def create_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
    """
    Creates and fits a scikit-learn preprocessing pipeline based on the training data.
    This pipeline handles numerical imputation/scaling, outlier capping, and categorical one-hot encoding.
    """
    logger.info("Creating feature preprocessing pipeline...")

    # --- NEW ROBUST FEATURE TYPE IDENTIFICATION LOGIC ---
    final_numeric_features = []
    final_categorical_features = []

    for col in X_train.columns:
        # Exclude known non-feature columns that might be present
        if col in ['person_id', 'time_to_event_days', 'event_observed', 'time_0_dt', 'obs_end_dt', 'actual_outcome_dt']:
            continue # Skip these internal columns

        if pd.api.types.is_numeric_dtype(X_train[col]):
            # Check if a numeric column is actually binary (0/1) and should be treated as categorical
            unique_non_nan_values = X_train[col].dropna().unique()
            if len(unique_non_nan_values) <= 2 and all(val in [0.0, 1.0] for val in unique_non_nan_values):
                final_categorical_features.append(col) # Treat as categorical (e.g., binary flags)
            else:
                final_numeric_features.append(col) # True numeric
        elif pd.api.types.is_object_dtype(X_train[col]) or pd.api.types.is_categorical_dtype(X_train[col]) or pd.api.types.is_bool_dtype(X_train[col]):
            final_categorical_features.append(col)
        # Other column types will be dropped by remainder='drop'
    # --- END NEW LOGIC ---

    if not final_numeric_features and not final_categorical_features:
        logger.warning("No numeric or categorical features identified for preprocessing. Returning a dummy preprocessor.")
        return ColumnTransformer(transformers=[('passthrough', 'passthrough', [])])

    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='mean')),
        ('outlier_capper', OutlierCapper(lower_bound_quantile=0.01, upper_bound_quantile=0.99)),
        ('scaler', StandardScaler())
    ])

    # categorical_transformer = Pipeline(steps=[
    #     ('imputer', SimpleImputer(strategy='most_frequent')),
    #     ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False, drop='first'))
    # ])
    categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    # Change this line:
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)) # <--- REMOVED drop='first'
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, final_numeric_features), # Use the new list
            ('cat', categorical_transformer, final_categorical_features) # Use the new list
        ],
        remainder='drop' # Explicitly 'drop' columns not handled
    )
    
    preprocessor.fit(X_train) 
    logger.info("Feature preprocessing pipeline created and fitted.")
    return preprocessor
    
def apply_preprocessing(
    preprocessor: ColumnTransformer,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]: # Explicitly return DataFrames
    """
    Applies the fitted preprocessing pipeline to both training and test data,
    returning them as DataFrames with feature names.
    """
    logger.info("Applying preprocessing to training data...")
    X_train_processed_array = preprocessor.transform(X_train) 

    if hasattr(X_train_processed_array, 'toarray'):
        X_train_processed_array = X_train_processed_array.toarray()

    feature_names = preprocessor.get_feature_names_out()

    X_train_processed = pd.DataFrame(X_train_processed_array, columns=feature_names, index=X_train.index) # Keep original index for context


    logger.info("Applying preprocessing to test data...")
    X_test_processed_array = preprocessor.transform(X_test)
    if hasattr(X_test_processed_array, 'toarray'):
        X_test_processed_array = X_test_processed_array.toarray()
    X_test_processed = pd.DataFrame(X_test_processed_array, columns=feature_names, index=X_test.index) # Keep original index for context
    #   logger.info(f"Processed X_train shape: {X_train_processed.shape}, dtype: {X_train_processed.dtypes}")
    logger.info(f"Processed X_train shape: {X_train_processed.shape}, dtypes: {X_train_processed.dtypes.to_dict()}") # .to_dict() makes it more readable
    logger.info(f"Processed X_test shape: {X_test_processed.shape}, dtype: {X_test_processed.dtypes}")
    return X_train_processed, X_test_processed