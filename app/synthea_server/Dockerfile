FROM python:3.13-slim

# Install Java and other dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Java environment
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Install Poetry
ENV POETRY_VERSION=1.8.3
RUN pip install poetry==$POETRY_VERSION

WORKDIR /app

# Download Synthea
RUN curl -L -o synthea-with-dependencies.jar \
    https://github.com/synthetichealth/synthea/releases/download/v3.2.0/synthea-with-dependencies.jar

# Copy your Python app files
COPY pyproject.toml ./
RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY synthea-pyserver ./synthea-pyserver

COPY README.md ./
COPY modules ./modules
RUN poetry install --no-interaction --no-ansi

# Create necessary directories and set permissions
RUN mkdir -p /app/modules /shared && \
    chmod -R 755 /app/modules && \
    ln -s /app/modules /shared/modules

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "synthea-pyserver.main:app", "--host", "0.0.0.0", "--port", "8000"]