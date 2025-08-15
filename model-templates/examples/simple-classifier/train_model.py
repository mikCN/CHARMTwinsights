#!/usr/bin/env python3
"""
Train a simple classifier for the CHARMTwinsights example.
This creates a dummy model that predicts risk based on age and BMI.
"""
import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

def create_dummy_model():
    """Create a simple logistic regression model"""
    # Create a pipeline with scaling and logistic regression
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(random_state=42))
    ])
    
    # Generate some dummy training data
    # Features: age, bmi, smoking (0/1)
    np.random.seed(42)
    n_samples = 1000
    
    X = np.random.rand(n_samples, 3)
    X[:, 0] = X[:, 0] * 60 + 20  # age: 20-80
    X[:, 1] = X[:, 1] * 20 + 18  # bmi: 18-38
    X[:, 2] = np.random.binomial(1, 0.3, n_samples)  # smoking: 0 or 1
    
    # Create target: higher risk for older, higher BMI, smoking
    risk_score = (X[:, 0] - 40) * 0.02 + (X[:, 1] - 25) * 0.1 + X[:, 2] * 0.5
    y = (risk_score + np.random.normal(0, 0.2, n_samples)) > 0.3
    
    # Train the model
    model.fit(X, y)
    
    return model

def main():
    print("Creating simple classifier model...")
    
    model = create_dummy_model()
    
    # Save the model
    with open('simple_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("Model saved as simple_model.pkl")
    
    # Test the model
    test_data = [[45, 28.5, 1], [30, 22.0, 0]]  # age, bmi, smoking
    predictions = model.predict_proba(test_data)
    
    print("\nTest predictions:")
    for i, (data, pred) in enumerate(zip(test_data, predictions)):
        print(f"  Patient {i+1}: age={data[0]}, bmi={data[1]}, smoking={data[2]} -> risk={pred[1]:.3f}")

if __name__ == "__main__":
    main()
