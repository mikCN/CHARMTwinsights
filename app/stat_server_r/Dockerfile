# Use an official plumber image with a recent R version.
FROM rstudio/plumber:latest

# Set working directory.
WORKDIR /

# We need some R packages: tidyverse, fhircrackr
# and plumber.

# Expose the port where plumber will serve the API.
EXPOSE 8000

# Copy the plumber API file into the container.
COPY . .

RUN Rscript -e "install.packages('dplyr', repos='https://cloud.r-project.org/')"
RUN Rscript -e "install.packages('openssl', repos='https://cloud.r-project.org/')"
RUN Rscript -e "install.packages('fhircrackr', repos='https://cloud.r-project.org/')"

# Run the plumber API on container startup.
CMD ["Rscript", "run_app.R"]
