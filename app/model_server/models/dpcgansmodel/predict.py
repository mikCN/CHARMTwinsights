
#!/usr/bin/env python3
import sys
import json
import pandas as pd
import pickle
import numpy as np

# Suppress warnings for cleaner output in default models
import warnings
warnings.filterwarnings('ignore')


def main():
    if len(sys.argv) not in [2, 3]:
        print("Usage: predict.py <input.json> [output.json]", file=sys.stderr)
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None

    print("Loading DPCGANS model...", file=sys.stderr)
    
    try:
        with open('dpcgan_model.pkl', 'rb') as inp:
            model = pickle.load(inp)
        
        print("Model loaded successfully", file=sys.stderr)

        # Load input features
        with open(input_file) as f:
            X = json.load(f)
        
        print(f"Processing {len(X)} generation requests", file=sys.stderr)
        
        res = []
        for i, x in enumerate(X):
            print(f"Generating synthetic data for request {i+1}/{len(X)}", file=sys.stderr)
            yhat = model.sample(**x)
            # result is a df; we need to convert NaNs to Nones so we can serialize to json properly
            yhat = yhat.replace({np.nan: None})
            res.append(yhat.to_dict(orient="records"))

        print(f"Successfully generated {len(res)} synthetic datasets", file=sys.stderr)

        # Output results
        if output_file:
            # New file-based I/O pattern
            with open(output_file, 'w') as f:
                json.dump(res, f, indent=2)
            print(f"Synthetic data written to {output_file}")
        else:
            # Legacy stdout pattern for backwards compatibility
            print(json.dumps(res))
            
    except Exception as e:
        print(f"Error during synthetic data generation: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
