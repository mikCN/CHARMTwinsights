#!/bin/bash

# test list models
echo -e "Models list:"
curl -X GET "http://localhost:8003/models" -H "Content-Type: application/json"

ehco -e "\n\nModel readme"
curl -s http://localhost:8003/models/irismodel:1.2.0/readme

echo -e "\n\nModel examples"
curl -s http://localhost:8003/models/irismodel:1.2.0/examples