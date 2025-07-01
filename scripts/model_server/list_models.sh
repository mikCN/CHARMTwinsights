#!/bin/bash

# test list models
echo -e "Models list:\n"
curl -X GET "http://localhost:8003/models" -H "Content-Type: application/json"

echo -e "\n\nDPCGAN Model detail:\n"
curl -s http://localhost:8003/models/dpcgansmodel:1.3.0

echo -e "\n"