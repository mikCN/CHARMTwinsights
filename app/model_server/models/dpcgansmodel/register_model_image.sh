#!/bin/bash


echo -e "Pushing dpcgans model to the model server...\n"
curl -X POST "http://localhost/modeling/models" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "dpcgansmodel:latest",
    "title": "Differentially Private Conditional GANs",
    "short_description": "A model for generating tabular data with privacy guarantees.",
    "authors": "TBD",
    "examples": [
      {"num_rows": 3, "max_retries": 100, "max_rows_multiplier": 10, "float_rtol": 0.01, "graceful_reject_sampling": false},
      {"num_rows": 4, "max_retries": 100, "max_rows_multiplier": 10, "float_rtol": 0.01, "graceful_reject_sampling": false}
    ],
    "readme": "## DPCGANS\nThis model implements a differentially private GAN for synthetic data."
  }'