#!/bin/bash

# test list models
echo -e "Iris model prediction:\n"
curl -X POST http://localhost:8003/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "irismodel:1.2.0", "input": [{"sepal length (cm)": 5.1, "sepal width (cm)": 3.5, "petal length (cm)": 1.4, "petal width (cm)": 0.2}, {"sepal length (cm)": 4.9, "sepal width (cm)": 3.0, "petal length (cm)": 1.4, "petal width (cm)": 0.2}]}'

echo -e "\n\nDPCGAN model prediction:\n"
curl -X POST http://localhost:8003/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "dpcgansmodel:1.2.0", "input": [{"num_rows": 3, "max_retries": 100, "max_rows_multiplier": 10, "float_rtol": 0.01, "graceful_reject_sampling": false}]}'

echo -e "\n"