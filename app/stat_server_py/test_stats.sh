#!/bin/bash

APP_PORT=${APP_PORT:-8000}


echo -e "Fetching data for 10 male patients:\n"
sleep 1
curl -X 'GET' \
  "http://localhost:$APP_PORT/stats/patients?gender=male&_count=10" \
  -H 'accept: application/json'

sleep 1
echo -e "\n\nFetching normal pregnancy conditions (SNOMED CT code 72892002):\n"
sleep 1
curl -X 'GET' \
  "http://localhost:$APP_PORT/stats/conditions?code=http%3A%2F%2Fsnomed.info%2Fsct%7C72892002" \
  -H 'accept: application/json'