#!/bin/bash

curl -X POST "http://localhost:8003/models" -H "Content-Type: application/json" -d '{"image": "irismodel:1.2.0"}'