#!/bin/bash

APP_PORT=${APP_PORT:-8000}

echo -e "Iris model prediction:\n"
curl -X POST http://localhost:$APP_PORT/modeling/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "irismodel:latest", "input": [{"sepal length (cm)": 5.1, "sepal width (cm)": 3.5, "petal length (cm)": 1.4, "petal width (cm)": 0.2}, {"sepal length (cm)": 4.9, "sepal width (cm)": 3.0, "petal length (cm)": 1.4, "petal width (cm)": 0.2}]}'

echo -e "\n\nDPCGAN model prediction:\n"
curl -X POST http://localhost:$APP_PORT/modeling/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "dpcgansmodel:latest", "input": [{"num_rows": 3, "max_retries": 100, "max_rows_multiplier": 10, "float_rtol": 0.01, "graceful_reject_sampling": false}]}'

echo -e "\n\n--- Testing coxcopdmodel prediction endpoint:\n"
curl -X POST http://localhost:$APP_PORT/modeling/predict \
  -H "Content-Type: application/json" \
  -d '{
    "image": "coxcopdmodel:latest",
    "input": [
      {
        "ethnicity": "Not Hispanic or Latino", 
        "sex_at_birth": "Female", 
        "obesity": 0.0, 
        "diabetes": 0.0, 
        "cardiovascular_disease": 0.0, 
        "smoking_status": "Never", 
        "alcohol_use": 0.0, 
        "bmi": 25.0, 
        "age_at_time_0": 50.0
      },
      {
        "ethnicity": "Hispanic or Latino", 
        "sex_at_birth": "Male", 
        "obesity": 1.0, 
        "diabetes": 1.0, 
        "cardiovascular_disease": 1.0, 
        "smoking_status": "Current", 
        "alcohol_use": 1.0, 
        "bmi": 32.0, 
        "age_at_time_0": 65.0
      },
      {
        "ethnicity": "Not Hispanic or Latino", 
        "sex_at_birth": "Female", 
        "obesity": 0.0, 
        "diabetes": 0.0, 
        "cardiovascular_disease": 0.0, 
        "smoking_status": "Never", 
        "alcohol_use": 0.0, 
        "bmi": 28.0, 
        "age_at_time_0": 45.0
      }
    ]
  }'

echo -e "\n\nPrediction test for coxcopdmodel sent."
echo -e "\n"