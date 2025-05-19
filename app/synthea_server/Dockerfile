FROM synthetichealth/synthea:latest

# Create a volume specifically for the modules
VOLUME /app/modules

# Make sure modules are readable by other containers/services
RUN chmod -R 755 /app/modules

# Expose modules directory via a standardized path
RUN mkdir -p /shared && ln -s /app/modules /shared/modules

# Your other Dockerfile instructions
WORKDIR /app



# Use an official lightweight Python image.
FROM ubuntu:24.10

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libmagic1 \
    file \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    python3.13 \
    python3.13-dev \
    python3.13-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.0.1
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION
ENV PATH="/root/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y \
    openjdk-21-jdk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Download the Synthea jar file and copy required modules folder
#RUN curl -L -o synthea-with-dependencies.jar https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar
RUN curl -L -o synthea-with-dependencies.jar https://github.com/synthetichealth/synthea/releases/download/v3.2.0/synthea-with-dependencies.jar
COPY modules ./modules

# Copy install dependencies first to leverage Docker cache
COPY pyproject.toml ./
RUN poetry install --no-interaction --no-ansi --only main --no-root

# then copy the main package and install it
COPY synthea-pyserver ./synthea-pyserver
COPY README.md ./
RUN poetry install --no-interaction --no-ansi

# NUM_PATIENTS and NUM_YEARS are set in the docker-compose.yml file
# they may be overridden when running the generation script, ala
# NUM_YEARS=1 NUM_PATIENTS=10 scripts/synthea_data_gen.sh

# https://github.com/synthetichealth/synthea/blob/master/src/main/resources/synthea.properties
# CMD rm -rf synthea_output/* && \
#     java -jar synthea-with-dependencies.jar \
#         -d modules \
#         --exporter.baseDirectory synthea_output \
#         --exporter.fhir.use_us_core_ig true \
#         -p ${NUM_PATIENTS} \
#         --exporter.years_of_history ${NUM_YEARS} \
#         ${EXTRA_ARGS} \
#         --exporter.csv.export true

# Expose the port FastAPI will run on.
EXPOSE 8000

# Run the application.
CMD ["poetry", "run", "uvicorn", "synthea-pyserver.main:app", "--host", "0.0.0.0", "--port", "8000"]
