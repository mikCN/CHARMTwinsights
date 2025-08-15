#!/usr/bin/env python3
"""
Create a minimal model file for the example without requiring dependencies.
This just creates a pickle file that can be loaded by the predict script.
"""
import pickle

# Create a very simple "model" class that just returns dummy predictions
class SimpleClassifier:
    def predict(self, X):
        """Dummy predictions based on simple rules"""
        predictions = []
        for row in X:
            age, bmi, smoking = row[0], row[1], row[2]
            # Simple rule: high risk if age > 50 OR bmi > 30 OR smoking
            risk = 1 if (age > 50 or bmi > 30 or smoking == 1) else 0
            predictions.append(risk)
        return predictions
    
    def predict_proba(self, X):
        """Dummy probability predictions"""
        probabilities = []
        for row in X:
            age, bmi, smoking = row[0], row[1], row[2]
            # Calculate risk score
            risk_score = (age - 40) * 0.01 + (bmi - 25) * 0.02 + smoking * 0.3
            risk_prob = max(0.1, min(0.9, 0.5 + risk_score))
            probabilities.append([1 - risk_prob, risk_prob])
        return probabilities

# Create and save the model
model = SimpleClassifier()

with open('simple_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Created simple_model.pkl")
print("This is a dummy model for demonstration purposes.")
