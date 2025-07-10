#!/bin/bash

# List of cohort IDs (space-separated)
cohort_ids=("cohort1" "cohort2" "cohort3")

for cohort_id in "${cohort_ids[@]}"; do
  echo "Processing cohort_id: $cohort_id"
  while true; do
    # Capture body and status code
    response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8002/synthetic-patients/push?num_patients=3&num_years=1&cohort_id=$cohort_id")
    # The last line is the HTTP status code
    http_code=$(echo "$response" | tail -n1)
    # Everything before is the body
    body=$(echo "$response" | sed '$d')

    echo "HTTP $http_code"
    echo "Response:"
    echo "$body"

    if [ "$http_code" -eq 200 ]; then
      echo "Server responded with 200 OK for $cohort_id."
      break
    else
      echo "Server not ready (status: $http_code). Retrying in 2 seconds..."
      sleep 2
    fi
  done
done

