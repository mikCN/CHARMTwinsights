"""
Configuration file for the regression model.
This file defines the feature columns, target column, and risk threshold,
and allows for environment-based overrides for flexibility.
"""

import os
import yaml

# Load YAML from 'configuration.yaml' (default or via env var)
CONFIG_YAML_PATH = os.getenv("CONFIG_YAML_PATH", "configuration.yaml")

def load_yaml_config(yaml_path=CONFIG_YAML_PATH):
    try:
        with open(yaml_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML configuration file not found: {yaml_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")

def get_feature_columns(config):
    """
    Extract feature column names from YAML config, or override via FEATURE_COLUMNS env var.
    """
    features_override = os.getenv("FEATURE_COLUMNS")
    if features_override:
        return [col.strip() for col in features_override.split(",") if col.strip()]
    
    features = config.get("features", [])
    return [f["name"] for f in features if "name" in f]

def get_target_column(config):
    """
    Get the outcome column name from YAML config, or override via TARGET_COLUMN env var.
    """
    return os.getenv("TARGET_COLUMN", config.get("outcome", {}).get("name", "disease_outcome"))

def get_risk_threshold():
    """
    Risk threshold defaults to 0.5, can be overridden via env.
    """
    try:
        threshold = float(os.getenv("RISK_THRESHOLD", "0.5"))
        if not (0 <= threshold <= 1):
            raise ValueError
        return threshold
    except ValueError:
        raise ValueError("RISK_THRESHOLD must be a float between 0 and 1.")

# Load YAML config
CONFIG = load_yaml_config()

# Exported config values
FEATURE_COLUMNS = get_feature_columns(CONFIG)
TARGET_COLUMN = get_target_column(CONFIG)
RISK_THRESHOLD = get_risk_threshold()

# Optional debug output
if __name__ == "__main__":
    print("YAML config loaded from:", CONFIG_YAML_PATH)
    print("Feature columns:", FEATURE_COLUMNS)
    print("Target column:", TARGET_COLUMN)
    print("Risk threshold:", RISK_THRESHOLD)
