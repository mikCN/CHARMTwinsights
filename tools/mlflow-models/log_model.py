import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y)

model = LogisticRegression(max_iter=200)
model.fit(X_train, y_train)

# Option 1: Save model to a local folder for later transfer
mlflow.sklearn.save_model(model, path="model_export")
