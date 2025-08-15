# Use an official lightweight Python image.
FROM python:3.13-slim

# Install system dependencies, including libmagic.
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libmagic1 \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry directly with pip
RUN pip install poetry==2.0.1

# Verify Poetry installation
RUN poetry --version

# Set the working directory.
WORKDIR /app

# Copy dependency management files.
COPY pyproject.toml ./

# install just the dependencies to start
RUN poetry install --no-interaction --no-ansi --only main --no-root

# then copy the main package
COPY model_server ./model_server

# Copy built-in model metadata maintaining directory structure
COPY models/ /app/builtin_models/

# then install the main package for use
RUN poetry install --no-interaction --no-ansi

# Expose the port FastAPI will run on.
EXPOSE 8000

# Run the application.
CMD ["poetry", "run", "uvicorn", "model_server.main:app", "--host", "0.0.0.0", "--port", "8000"]