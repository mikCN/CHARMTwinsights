

# CHARMTwinsight

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation and Usage](#installation-and-usage)
    - [0. Prerequisites](#0-prerequisites)
    - [1. Build and Start Application](#1-build-and-start-application)
    - [2. Generate Synthetic Data](#2-generate-synthetic-data)
    - [3. Test Models](#3-test-models)
    - [4. Test Analytics](#4-test-analytics)
    - [5. Stopping and Cleaning Up](#5-stopping-and-cleaning-up)
4. [Troubleshooting](#troubleshooting)
5. [Model Development](#model-development)
6. [Development](#development)
    - [Recommendations](#recommendations)
    - [Iterating](#iterating)
7. [Miscellaneous](#miscellaneous)

## Overview

CHARMTwinsight is part of the [CHARM](https://github.com/CHARM-BDF/) suite of tools, focused on health data storage, predictive analytics, and synthetic data generation.

It is under active development, and currently supports the following features via REST API:

- Synthetic patient data generation with [Synthea](https://synthea.mitre.org/).
- Internal FHIR data storage and cohort management with [HAPI FHIR](https://hapifhir.io/).
- Data summary statistics and querying.
- Predictive analytics, supporting health risk models and synthetic data generation with GAN and similar models.

## Architecture

CHARMTwinsight is designed as a microservices architecture managed with `docker compose`. 

<img src="app/arch.png" style="align: center" width="90%">

*Note: this architecture represents implemented data flows; future features may connect HAPI FHIR to the model server, etc.*

**`router`**: Externally-facing REST API providing access to backend services. Built with FastAPI for flexibility.

**`hapi`**: HAPI FHIR server for efficient and flexible storage and querying of FHIR data.

**`hapi_db`**: Postgres database providing storage for HAPI.

**`synthea_server`**: REST API frontend to the Synthea synthetic data generator; generates FHIR data and corresponding cohort IDs for storage in HAPI.

**`stat_server_r`**: REST API for R-based analytics (summary statistics etc.) on stored FHIR or other data. Uses `plumbr` and `fhircrackr` R libraries, amongst others.

**`stat_server_py`**: REST API for Python-based analytics (summary statistics etc.) on stored FHIR or other data. Uses `FastAPI`, `fhiry`, and other Python libraries.

**`model_server`**: REST API hosting and serving arbitrary ML and statistical models packaged as Docker containers. 

**`model_server_db`**: MongoDB database for storing metadata on hosted models.


## Installation and Usage

### 0. Prerequisites

You will need `docker`; if using a Mac install [Docker Desktop](https://www.docker.com/products/docker-desktop/).

- Mac users may also wish to install GNU versions of [coreutils](https://formulae.brew.sh/formula/coreutils)
- **Mac users may also need to enable Docker volume storage under `System Preferences -> Privacy and Security -> Files and Folders -> Docker`**

### 1. Build and Start Application

**New simplified process:** CHARMTwinsights now automatically builds and registers all components in one step.

```bash
# working dir: app
./build_all.sh
docker compose up --detach
```

The `build_all.sh` script builds both the application images and the built-in ML models. All `docker compose` commands need to be run in the same directory as the `docker-compose.yml` file.

The main API endpoints will be browsable at [`http://localhost:8000/docs`](http://localhost:8000/docs). All built-in models (IrisModel, CoxCOPDModel, DPCGANSModel) will be automatically available.


### 2. Generate Synthetic Data

Synthetic patient data in FHIR format may be generated via a POST request to http://localhost:8000/synthetic/synthea/generate-synthetic-patients, with url parameters `num_patients`, `num_years`, 
and `cohort_id`. The patients will be simulated with Synthea, and their records will be tagged with the provided `cohort_id` (defaulting to `default`).

It is possible to re-use the same cohort ID across multiple generations, in which case newly generated patients will be added to the cohort.

A testing script demonstrates this (retrying until the Synthea and HAPI services are up and running), creating a `cohort1` with 6 members, and a `cohort2` with 3. Each generation takes a few seconds.

```bash
# working dir: app
synthea_server/gen_patients.sh
```

These data are pushed to the FHIR server accessible at `http://localhost:8080` for development purposes.

### 3. Test Models

Predictive model capabilities are accessed under endpoints at `http://localhost:8000/modeling`. Example CURLs are available via script:

```bash
# working dir: app
model_server/models/test_predict_models.sh
```

As above, skip if you are not developing or using models.

### 4. Test Analytics

Summary statistics about generated patient data are available under endpoints at `http://localhost:8000/stats`. Examples CURLs are available via script:

```bash
# working dir: app
stat_server_py/test_stats.sh
```

### 5. Stopping and Cleaning Up

#### Basic Stop
To stop the application but keep generated/imported FHIR data:
```bash
# working dir: app
docker compose down
```

#### Full Reset
To completely reset everything (useful if you encounter issues):

```bash
# working dir: app
# Stop all services
docker compose down

# Remove stored FHIR data (optional - this data takes time to regenerate)
rm -rf hapi/postgres_data/*

# For a completely fresh start, you can also remove model metadata
# (models will be automatically re-registered on next startup)
docker volume rm app_shared_tmp 2>/dev/null || true
```

**Note:** The FHIR database data is persisted in `hapi/postgres_data/` to avoid having to regenerate synthetic patients every time. Model metadata is stored in MongoDB and will be automatically recreated when you restart.

#### Nuclear Option (Use with Caution)
If you're experiencing persistent Docker issues, you can use the cleanup script:
```bash
# working dir: project root
scripts/docker_clean.sh
```
**WARNING:** This script removes ALL Docker containers and networks on your system, not just CHARMTwinsights!

## Troubleshooting

Having Docker issues? See [DOCKER_TIPS.md](DOCKER_TIPS.md) for detailed troubleshooting help.

**Quick fixes:**
- **Won't start:** Make sure Docker Desktop is running
- **Port conflicts:** Run `docker compose down` first  
- **Build errors:** Try `./build_all.sh --no-cache`
- **Still broken:** `docker compose down && ./build_all.sh && docker compose up --detach`

## Model Development

CHARMTwinsights provides templates and tools to help developers create new machine learning models without needing Docker expertise.

### Quick Start for Model Developers

1. **Choose a template:**
   ```bash
   # For Python models
   cp -r model-templates/python-model my-new-model
   
   # For R models  
   cp -r model-templates/r-model my-new-model
   ```

2. **Customize your model:**
   - Edit `predict.py` or `predict.R` with your model logic
   - Update `README.md` with model documentation
   - Update `examples.json` with test data
   - Add dependencies to `pyproject.toml` or `DESCRIPTION`

3. **Validate and build:**
   ```bash
   # Validate Dockerfile (prevents common mistakes)
   python model-templates/validate-dockerfile.py my-new-model/Dockerfile
   
   # Build Docker image
   docker build -t my-new-model:latest my-new-model/
   ```

4. **Register with CHARMTwinsights:**
   ```bash
   curl -X POST http://localhost:8000/modeling/models \
     -H "Content-Type: application/json" \
     -d '{
       "image": "my-new-model:latest",
       "title": "My New Model",
       "short_description": "What your model does",
       "authors": "Your Name"
     }'
   ```

### Key Features for Model Developers

- **Templates:** Ready-to-use Python and R model templates
- **Container-based metadata:** Include `README.md` and `examples.json` in your model container
- **Validation tools:** Prevent common Docker mistakes with automated validation
- **File-based I/O:** Models read JSON input files and write JSON output files
- **Example models:** Working examples to learn from

### Resources

- **Full guide:** [`model-templates/README.md`](model-templates/README.md)
- **Python template:** [`model-templates/python-model/`](model-templates/python-model/)
- **R template:** [`model-templates/r-model/`](model-templates/r-model/)
- **Working example:** [`model-templates/examples/simple-classifier/`](model-templates/examples/simple-classifier/)
- **Dockerfile validator:** [`model-templates/validate-dockerfile.py`](model-templates/validate-dockerfile.py)

## Development

### Recommendations

Ideally, features are added to the service they are most aligned with, adding additional services for feature sets sufficiently unique.
To keep with a microservice architecture, services should not share disk storage, but communicate over the docker-internal network via REST.

### Iterating

As noted above, FHIR data stored in the HAPI server is persisted across runs; this allows the developer to generate synthetic data
(a time-consuming process) once while while iterating on other features. 

For development purposes, each service is exposed to the localhost on independent ports (applied automatically via `app/docker-compose.override.yaml`):

- router: localhost:8000
- hapi: localhost:8080
- stat_server_py: localhost:8001
- stat_server_r: localhost:8002
- synthea_server: localhost:8003
- model_server: localhost:8004

*The HAPI server in particular is useful for browsing FHIR data and testing ad-hoc queries.*

Individual services can be rapidly iterated on even if they depend on others.
After the application has been initialized and databases populated, a typical workflow would be:

1. Initialize application as above in a detached state.
1. Make changes to service code (e.g. in `app/stat_server_py/pyserver/main.py`).

    - For Python services, add packages by running `poetry add <package-name>` next to the `pyproject.toml` file; for R services, add the package to the Dockerfile.

1. Rebuild relevant containers with `docker compose build --with-dependencies <service_name>`

    - This should only rebuild services that have changed and that are dependent on the service; Dockerfiles have also been designed to maximize use of layer caching for fast rebuilds. If you run into trouble and think caching or persistent data are causing issues, try these approaches in order:
   
      1. **Simple rebuild:** `docker compose build <service_name> --no-cache`
      2. **Reset service data:** `docker compose down && docker compose up --detach`  
      3. **Full reset:** `docker compose down && rm -rf hapi/postgres_data/* && ./build_all.sh --no-cache && docker compose up --detach`
      4. **Nuclear option:** Use `scripts/docker_clean.sh` (removes ALL Docker containers/networks on your system)

1. Restart the services with `docker compose up <service_name>`.

    - Re-upping only the relevant service will cause only it and dependent services that have changed to be re-initialized; you won't have to wait for HAPI or other dependent services to restart. Bringing up an an attached state, with a given target, will only show logs for the specific service (useful for print-debugging).

A common development loop is thus simply `docker compose build --with-dependencies <service_name> && docker compose up <service_name>`, using Ctrl-C and rerunning to effectuate code changes, accessing services directly on their local port for testing (e.g. `http://localhost:8001` for `stat_server_py`).

## Miscellaneous

### Additional Documentation
- [`DOCKER_TIPS.md`](DOCKER_TIPS.md): Comprehensive Docker troubleshooting guide for beginners
- [`model-templates/`](model-templates/): Templates and guides for developing new models

### Useful Scripts
The `scripts` folder contains a few useful scripts:

- `docker_status.sh`: list various running docker resources
- `docker_clean.sh`: clobber running docker resources (containers, networks, volumes)
- `mimic_fetch_decrypt.sh`: fetch MIMIC IV FHIR data and decrypt it (MIMIC IV access approval required, contact Shawn for password)
- `mimic_sample_push_hapi.py`: pushes a rich subsample of the MIMIC IV FHIR data to the running HAPI server for testing