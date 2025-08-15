# CHARMTwinsights Python Model Template
# 
# IMPORTANT: Do NOT add CMD or ENTRYPOINT directives!
# The model server handles execution automatically.

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for dependency management
RUN pip install poetry==1.8.2

# Set working directory
WORKDIR /app

# Copy dependency files first (for better Docker layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-interaction --no-root --only main

# Copy your model files
COPY predict.py ./
COPY predict ./
COPY README.md ./
COPY examples.json ./

# Copy your model artifacts (adjust as needed)
# COPY model_artifacts/ ./model_artifacts/
# COPY *.pkl ./
# COPY *.joblib ./

# Make the predict script executable
RUN chmod +x predict

# DO NOT ADD CMD OR ENTRYPOINT - The model server handles execution
