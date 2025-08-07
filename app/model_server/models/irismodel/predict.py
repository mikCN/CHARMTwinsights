#!/usr/bin/env python3
import sys
import pandas as pd
import mlflow.sklearn
import json

MODEL_PATH = "iris_model"

def main():
    if len(sys.argv) != 2:
        print("Usage: predict <input.json>", file=sys.stderr)
        sys.exit(1)
    input_file = sys.argv[1]
    # Load input features
    with open(input_file) as f:
        X = pd.read_json(f)
    # Load model
    model = mlflow.sklearn.load_model(MODEL_PATH)
    # Make predictions
    preds = model.predict(X)
    print(json.dumps(preds.tolist()))

if __name__ == "__main__":
    main()
