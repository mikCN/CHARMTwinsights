#!/usr/bin/env python3
"""
Simple Classifier Example - CHARMTwinsights
Predicts health risk based on age, BMI, and smoking status.
"""
import sys
import json
import pandas as pd
import pickle

def load_model():
    """Load the trained model"""
    try:
        with open('simple_model.pkl', 'rb') as f:
            return pickle.load(f)
    except Exception:
        # Fallback to a simple rule-based model if pickle fails
        class SimpleClassifier:
            def predict(self, X):
                """Simple rule-based predictions"""
                predictions = []
                for row in X:
                    age, bmi, smoking = row[0], row[1], row[2]
                    # Simple rule: high risk if age > 50 OR bmi > 30 OR smoking
                    risk = 1 if (age > 50 or bmi > 30 or smoking == 1) else 0
                    predictions.append(risk)
                return predictions
            
            def predict_proba(self, X):
                """Simple probability predictions"""
                probabilities = []
                for row in X:
                    age, bmi, smoking = row[0], row[1], row[2]
                    # Calculate risk score
                    risk_score = (age - 40) * 0.01 + (bmi - 25) * 0.02 + smoking * 0.3
                    risk_prob = max(0.1, min(0.9, 0.5 + risk_score))
                    probabilities.append([1 - risk_prob, risk_prob])
                return probabilities
        
        return SimpleClassifier()

def preprocess_input(input_data):
    """Convert input to the format expected by the model"""
    # Convert to DataFrame
    if isinstance(input_data, list):
        df = pd.DataFrame(input_data)
    else:
        df = pd.DataFrame([input_data])
    
    # Ensure required columns exist with proper types
    required_cols = ['age', 'bmi', 'smoking']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Convert to numeric and extract as numpy array
    feature_data = df[required_cols].astype(float).values
    
    return feature_data, df

def postprocess_output(predictions, probabilities, original_df):
    """Format predictions into the expected output format"""
    results = []
    
    for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
        result = {
            "risk_prediction": int(pred),  # 0 = low risk, 1 = high risk
            "risk_probability": float(prob[1]),  # probability of high risk
            "confidence": float(max(prob))  # confidence in prediction
        }
        
        # Include patient ID if provided
        if 'id' in original_df.columns and i < len(original_df):
            result['id'] = original_df.iloc[i]['id']
        
        results.append(result)
    
    return results

def main():
    """Main prediction function"""
    if len(sys.argv) not in [2, 3]:
        print("Usage: predict.py <input.json> [output.json]", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    try:
        print("Loading simple classifier model...", file=sys.stderr)
        model = load_model()
        
        # Load input data
        with open(input_file, 'r') as f:
            input_data = json.load(f)
        
        print(f"Processing {len(input_data) if isinstance(input_data, list) else 1} record(s)", file=sys.stderr)
        
        # Preprocess input
        feature_data, original_df = preprocess_input(input_data)
        
        # Make predictions
        predictions = model.predict(feature_data)
        probabilities = model.predict_proba(feature_data)
        
        # Postprocess output
        results = postprocess_output(predictions, probabilities, original_df)
        
        print(f"Generated {len(results)} prediction(s)", file=sys.stderr)
        
        # Output results
        if output_file:
            # New file-based I/O pattern
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results written to {output_file}")
        else:
            # Legacy stdout pattern for backwards compatibility
            print(json.dumps(results))
            
    except Exception as e:
        print(f"Error during prediction: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
