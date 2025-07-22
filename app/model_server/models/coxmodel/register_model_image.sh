#!/bin/bash


echo -e "Registering Cox PH model to the model server...\n"
curl -X POST "http://localhost/modeling/models" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "coxmodel:latest",
    "title": "Cox PH Model for COPD Prediction",
    "short_description": "A survival model to predict risk and survival probability for COPD based on demographics and comorbidities.",
    "authors": "Lakshmi Anandan",
    "examples": [
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
      }
    ],
    "readme": "## Cox PH Model for COPD Prediction\n\nThis model implements a Cox Proportional Hazards model using `lifelines` for survival analysis of COPD. It predicts partial hazard scores (relative risk) and survival probabilities at 5 years (1825 days) based on a set of demographic and comorbidity features.\n\n**Input Features Expected:**\n- `ethnicity` (Categorical)\n- `sex_at_birth` (Categorical)\n- `obesity` (Binary)\n- `diabetes` (Binary)\n- `cardiovascular_disease` (Binary)\n- `smoking_status` (Categorical)\n- `alcohol_use` (Binary)\n- `bmi` (Continuous)\n- `age_at_time_0` (Continuous)\n\n**Output:**\n- `partial_hazard` (float): The individual\'s relative risk score.\n- `survival_probability_5_years` (float): The probability of remaining free from COPD for 5 years.\n\nThe model artifacts are pickled (`.pkl` files) and packaged for deployment using Poetry and Docker."
  }'