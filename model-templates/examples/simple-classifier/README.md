# Simple Health Risk Classifier

A basic example model that predicts health risk based on demographic and lifestyle factors.

## Features

- **age**: Patient age in years (20-80)
- **bmi**: Body Mass Index (18-40)
- **smoking**: Smoking status (0 = non-smoker, 1 = smoker)
- **id**: Optional patient identifier

## Output

- **risk_prediction**: Binary risk classification (0 = low risk, 1 = high risk)
- **risk_probability**: Probability of high risk (0.0-1.0)
- **confidence**: Model confidence in prediction (0.0-1.0)
- **id**: Patient identifier (if provided in input)

## Model Details

This is a simple logistic regression model trained on synthetic data. It uses:
- **Algorithm**: Logistic Regression with StandardScaler preprocessing
- **Features**: Age, BMI, smoking status
- **Training**: 1000 synthetic samples with realistic feature distributions
- **Performance**: Example model for demonstration purposes only

**Note**: This is a demonstration model with synthetic training data. Not for actual medical use.

## Usage

Send JSON input with patient data and receive risk predictions.

## Example Input

```json
[
  {
    "age": 45,
    "bmi": 28.5,
    "smoking": 1,
    "id": "patient_001"
  },
  {
    "age": 30,
    "bmi": 22.0,
    "smoking": 0,
    "id": "patient_002"
  }
]
```

## Example Output

```json
[
  {
    "risk_prediction": 1,
    "risk_probability": 0.72,
    "confidence": 0.72,
    "id": "patient_001"
  },
  {
    "risk_prediction": 0,
    "risk_probability": 0.23,
    "confidence": 0.77,
    "id": "patient_002"
  }
]
```

## Building This Example

```bash
# Train the model (creates simple_model.pkl)
python train_model.py

# Build the Docker image
docker build -t simple-classifier:latest .

# Register with CHARMTwinsights
curl -X POST http://localhost:8000/modeling/models \
  -H "Content-Type: application/json" \
  -d '{
    "image": "simple-classifier:latest",
    "title": "Simple Health Risk Classifier",
    "short_description": "Predicts health risk based on age, BMI, and smoking status",
    "authors": "CHARMTwinsights Team"
  }'
```
