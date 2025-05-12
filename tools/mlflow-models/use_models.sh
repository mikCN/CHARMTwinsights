echo "MODEL LISTING"
echo "===================="
curl http://localhost:8000/models

echo ""
echo "MODEL DETAILS"
echo "===================="
curl http://localhost:8000/models/iris_model

echo ""
echo "MODEL PREDICTION"
echo "===================="
curl -X POST http://localhost:8000/predict/iris_model -H "Content-Type: application/json" -d '{"data":[{"sepal length (cm)":5.1,"sepal width (cm)":3.5,"petal length (cm)":1.4,"petal width (cm)":0.2}]}'
