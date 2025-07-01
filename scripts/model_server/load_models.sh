#!/bin/bash


echo -e "Pushing dpcgans model to the model server...\n"
curl -X POST "http://localhost:8003/models" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "dpcgansmodel:1.3.0",
    "title": "Differentially Private Conditional GANs",
    "short_description": "A model for generating tabular data with privacy guarantees.",
    "authors": "TBD",
    "examples": [
      {"num_rows": 3, "max_retries": 100, "max_rows_multiplier": 10, "float_rtol": 0.01, "graceful_reject_sampling": false},
      {"num_rows": 4, "max_retries": 100, "max_rows_multiplier": 10, "float_rtol": 0.01, "graceful_reject_sampling": false}
    ],
    "readme": "## DPCGANS\nThis model implements a differentially private GAN for synthetic data."
  }'


echo -e "\n\nPushing iris model to the model server...\n"
curl -X POST "http://localhost:8003/models" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "irismodel:latest",
    "title": "Iris Dataset Model",
    "short_description": "A model for predicting iris species based on features.",
    "authors": "John Doe, Jane Smith",
    "examples": [
      {
        "sepal length (cm)": 5.1,
        "sepal width (cm)": 3.5,
        "petal length (cm)": 1.4,
        "petal width (cm)": 0.2
      },
      {
        "sepal length (cm)": 7.0,
        "sepal width (cm)": 3.2,
        "petal length (cm)": 4.7,
        "petal width (cm)": 1.4
      }    
    ],
    "readme": "## IrisModel\nThis model predicts the species of iris flowers based on their sepal and petal dimensions. It is trained on the classic Iris dataset and can classify iris species into three categories: Setosa, Versicolor, and Virginica."
  }'

echo -e "\n"