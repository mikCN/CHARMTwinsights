#!/bin/bash

APP_PORT=${APP_PORT:-8000}

echo -e "Registering Cox PH COPD model to the model server (using container-based metadata)...\n"
curl -X POST http://localhost:$APP_PORT/modeling/models \
  -H "Content-Type: application/json" \
  -d '{
    "image": "coxcopdmodel:latest",
    "title": "Cox PH Model for COPD Prediction",
    "short_description": "A survival model to predict risk and survival probability for COPD based on demographics and comorbidities.",
    "authors": "Lakshmi Anandan"
  }'
