
#!/usr/bin/env python3
import sys
import json
import pandas as pd
import pickle
import numpy as np


def main():
    if len(sys.argv) != 2:
        print("Usage: predict.py <input.json>", file=sys.stderr)
        sys.exit(1)
    input_file = sys.argv[1]

    with open('dpcgan_model.pkl', 'rb') as inp:
        model = pickle.load(inp)

    # Load input features
    with open(input_file) as f:
        X = json.load(f)
    
    res = []
    for x in X:
        yhat = model.sample(**x)
        # result is a df; we need to convert NaNs to Nones so we can serialize to json properly
        yhat = yhat.replace({np.nan: None})
        res.append(yhat.to_dict(orient="records"))


    print(json.dumps(res))

if __name__ == "__main__":
    main()
