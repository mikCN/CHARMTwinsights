# Use an official lightweight Python image.
FROM python:3.13-slim

# Install system dependencies, including libmagic.
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libmagic1 \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry.
ENV POETRY_VERSION=2.0.1
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION
ENV PATH="/root/.local/bin:${PATH}"

# Set the working directory.
WORKDIR /app

# Copy dependency management files.
COPY pyproject.toml ./

# install just the dependencies to start
RUN poetry install --no-interaction --no-ansi --only main --no-root

# then copy the main package - WHY IS THIS NOT WORKGINGGGGG
COPY router ./router

# then install the main package for use
RUN poetry install --no-interaction --no-ansi

# Expose the port FastAPI will run on.
EXPOSE 8000

# Run the application.
CMD ["poetry", "run", "uvicorn", "router.main:app", "--host", "0.0.0.0", "--port", "8000"]
