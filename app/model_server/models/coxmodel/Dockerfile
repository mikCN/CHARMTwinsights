
FROM python:3.10-slim

# Install system dependencies. 'build-essential' is crucial for many Python packages (numpy, scipy, etc.)
# 'curl' is needed for Poetry installer.
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry. Using the official installer script.
# Specify a recent, stable Poetry version
ENV POETRY_VERSION=1.8.2 
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION
ENV PATH="/root/.local/bin:${PATH}" 

# Set the working directory inside the container
WORKDIR /app

# Copy dependency management file (pyproject.toml)
COPY pyproject.toml ./

# Install dependencies. --no-root is correct here.
RUN poetry install --no-interaction --no-root --only main

# Create the directory for pickled models inside the container (RECOMMENDED)
RUN mkdir -p pickled_models

# Copy your pickled models folder into the image.
COPY pickled_models/ ./pickled_models/
COPY twinsight_model twinsight_model

# Copy your predict.py script AND the 'predict' executable shell script
# Ensure 'predict' (the shell script) exists locally in your coxmodel folder
COPY predict.py ./
COPY predict ./

# Make the 'predict' shell script executable
RUN chmod +x predict

# no entrypoint or cmd, that will be handled by the model server