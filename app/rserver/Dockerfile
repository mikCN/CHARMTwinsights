# Use an official plumber image with a recent R version.
FROM rstudio/plumber:latest

# Set working directory.
WORKDIR /

# We need some R packages: tidyverse, fhircrackr
# and plumber.

# Install the required R packages.
RUN Rscript -e "install.packages(c(\
    'dplyr', \
    'fhircrackr' \
    ), repos='https://cloud.r-project.org/')"

# Expose the port where plumber will serve the API.
EXPOSE 8000

# Copy the plumber API file into the container.
COPY . .

# Run the plumber API on container startup.
CMD ["Rscript", "run_app.R"]
