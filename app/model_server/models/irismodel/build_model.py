import os
import mlflow.sklearn
from mlflow.models.signature import infer_signature
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# Set the directory where you want to save the model
EXPORT_DIR = "iris_model"

# Load iris data
iris = load_iris(as_frame=True)
X, y = iris.data, iris.target

# Train/test split (just to be realistic)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)

# Train logistic regression
model = LogisticRegression(max_iter=200)
model.fit(X_train, y_train)

# Save model with mlflow
mlflow.sklearn.save_model(
    sk_model=model,
    path=EXPORT_DIR
)

print(f"MLflow model saved to: {EXPORT_DIR}")
