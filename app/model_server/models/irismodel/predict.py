#!/usr/bin/env python3
import sys
import pandas as pd
import mlflow.sklearn
import json

MODEL_PATH = "iris_model"

def main():
    if len(sys.argv) not in [2, 3]:
        print("Usage: predict <input.json> [output.json]", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    try:
        print("Loading iris model...", file=sys.stderr)
        
        # Load input features
        with open(input_file) as f:
            X = pd.read_json(f)
        
        print(f"Loaded {len(X)} samples for prediction", file=sys.stderr)
        
        # Load model
        model = mlflow.sklearn.load_model(MODEL_PATH)
        print("Model loaded successfully", file=sys.stderr)
        
        # Make predictions
        preds = model.predict(X)
        predictions = preds.tolist()
        
        print(f"Generated {len(predictions)} predictions", file=sys.stderr)
        
        # Output results
        if output_file:
            # New file-based I/O pattern
            with open(output_file, 'w') as f:
                json.dump(predictions, f, indent=2)
            print(f"Predictions written to {output_file}")
        else:
            # Legacy stdout pattern for backwards compatibility
            print(json.dumps(predictions))
            
    except Exception as e:
        print(f"Error during prediction: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
