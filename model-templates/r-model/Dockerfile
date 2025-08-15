# CHARMTwinsights R Model Template
# 
# IMPORTANT: Do NOT add CMD or ENTRYPOINT directives!
# The model server handles execution automatically.

FROM r-base:4.3.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy DESCRIPTION file for R dependencies
COPY DESCRIPTION ./

# Install R dependencies
RUN R -e "install.packages('renv')"
RUN R -e "install.packages(c('jsonlite', 'readr'))"  # Always needed
# Install your specific model dependencies listed in DESCRIPTION
RUN R -e "deps <- read.dcf('DESCRIPTION')[1, 'Depends']; if (!is.na(deps)) { pkgs <- trimws(strsplit(deps, ',')[[1]]); lapply(pkgs[pkgs != 'R'], install.packages) }"

# Copy your model files
COPY predict.R ./
COPY predict ./
COPY README.md ./
COPY examples.json ./

# Copy your model artifacts (adjust as needed)
# COPY model_artifacts/ ./model_artifacts/
# COPY *.rds ./
# COPY *.RData ./

# Make the predict script executable
RUN chmod +x predict

# DO NOT ADD CMD OR ENTRYPOINT - The model server handles execution
