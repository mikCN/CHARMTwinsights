import os
import tarfile
import mlflow.sklearn
from mlflow.models.signature import infer_signature
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_iris, load_wine
import pandas as pd

def train_model(dataset_func, model_name: str):
    data = dataset_func(as_frame=True)
    X = data.data
    y = data.target

    X_train, X_test, y_train, y_test = train_test_split(X, y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    return model, X_train, X_test, model_name

def save_mlflow_model(model, X_train, model_name: str):
    # Generate a clear signature using DataFrame with column names
    signature = infer_signature(X_train, model.predict(X_train))

    model_dir = f"{model_name}_export"
    mlflow.sklearn.save_model(
        sk_model=model,
        path=model_dir,
        signature=signature
    )
    return model_dir

def archive_model(model_dir: str):
    archive_path = f"{model_dir}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(model_dir, arcname=os.path.basename(model_dir))
    print(f"Packaged model: {archive_path}")

def main():
    for dataset_func, model_name in [
        (load_iris, "iris_model"),
        (load_wine, "wine_model")
    ]:
        model, X_train, X_test, name = train_model(dataset_func, model_name)
        model_dir = save_mlflow_model(model, X_train, name)
        archive_model(model_dir)

if __name__ == "__main__":
    main()
