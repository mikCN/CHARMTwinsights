# Simple Classifier Example for CHARMTwinsights
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.2

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-root --only main

COPY predict.py ./
COPY predict ./
COPY README.md ./
COPY examples.json ./
COPY train_model.py ./
COPY simple_model.pkl ./

RUN chmod +x predict
