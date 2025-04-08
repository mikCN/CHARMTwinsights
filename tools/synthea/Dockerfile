# Use a recent OpenJDK image (you can adjust the version as needed)
FROM openjdk:23-slim

# Set working directory
WORKDIR /app

# Install curl for downloading the Synthea jar
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create directories for Synthea and its output
RUN mkdir -p synthea_output

# Copy the modules directory (required by Synthea) into the image
COPY modules ./modules

# Download the Synthea jar file into the synthea directory
RUN curl -L -o synthea-with-dependencies.jar https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar

# NUM_PATIENTS and NUM_YEARS are set in the docker-compose.yml file
# they may be overridden when running the generation script, ala
# NUM_YEARS=1 NUM_PATIENTS=10 scripts/synthea_data_gen.sh

# https://github.com/synthetichealth/synthea/blob/master/src/main/resources/synthea.properties
CMD rm -rf synthea_output/* && \
    java -jar synthea-with-dependencies.jar \
        -d modules \
        --exporter.baseDirectory synthea_output \
        --exporter.fhir.use_us_core_ig true \
        -p ${NUM_PATIENTS} \
        --exporter.years_of_history ${NUM_YEARS} \
        ${EXTRA_ARGS} \
        --exporter.csv.export true
