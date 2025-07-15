

# CHARMTwinsight

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

### 1. Build Application Images

First, build the images for the application with `docker compose`. All `docker compose` commands need to be run in the same directory as the `docker-compose.yml` file.

```bash
# working dir: app
docker compose build
```

If you are having trouble, you might add a `--no-cache` to force rebuilding images from scratch, and/or a `--progress=plain` to see complete build progress and error logs.

### 2. Build Model Images

Next, build the default images for the model-hosting service. These default models may be complemented with other Docker-based models via the API, provided the referenced images are on the same host as the app, or available on Dockerhub or another container registry. You can skip this step if you don't intend to use the predefined models.

```bash
# working dir: app
model_server/models/build_model_images.sh
```

You can add build args to this script, e.g. `--no-cache` to force rebuilding the model images.

### 3. Start App

Using `docker compose`:

```bash
# working dir: app
docker compose up --detach
```

This starts all services in the application in a 'detached' state; subsequent docker compose commands (e.g. `docker compose logs`, `docker compose down`) can be used for management. 

The main API endpoints will be browsable at [`http://localhost/docs`](http://localhost/docs).

### 4. Load Models

The default set of predictive and generative models must be registered with the model server before use. You can skip this step if you
don't intend to use the predefined models.

```bash
# working dir: app
model_server/models/register_model_images.sh
```

Each model will be tested with the example inputs, returning the generated results.


### 5. Generate Synthetic Data

Synthetic patient data in FHIR format may be generated via a POST request to http://localhost/synthetic/synthea/generate-synthetic-patients, with url parameters `num_patients`, `num_years`, 
and `cohort_id`. The patients will be simulated with Synthea, and their records will be tagged with the provided `cohort_id` (defaulting to `default`).

It is possible to re-use the same cohort ID across multiple generations, in which case newly generated patients will be added to the cohort.

A testing script demonstrates this (retrying until the Synthea and HAPI services are up and running), creating a `cohort1` with 6 members, and a `cohort2` with 3. Each generation takes a few seconds.

```bash
# working dir: app
synthea_server/gen_patients.sh
```

These data are pushed to the FHIR server accessible at `http://localhost:8080` for development purposes.

### 6. Test Predictive Models

Predictive model capabilities are accessed under endpoints at `http://localhost/modeling`. Example CURLs are available via script:

```bash
# working dir: app
model_server/models/test_predict_models.sh
```

As above, skip if you are not developing or using models.

### 7. Test Summary Statistics

Summary statistics about generated patient data are available under endpoints at `http://localhost/stats`. Examples CURLs are available via script:

```bash
# working dir: app
stat_server_py/test_stats.sh
```

### 8. Cleaning up

Use docker compose to stop the services and cleanup:

```bash
# working dir: app
docker compose down
```

Because generating and loading synthetic data into the FHIR server is time consuming, data for the backing Postgres 
database **is persisted**. To remove this data, simply remove the files in `app/hapi/postgres_data/`:

```bash
# working dir: app
rm -rf hapi/postgres_data/*
```

Other data are not persisted (e.g. model metadata loaded into the `model_server`), though any built model docker images will remain on your local machine unless removed via docker commands (or Docker Desktop).

## Development

### Recommendations

Ideally, features are added to the service they are most aligned with, adding additional services for feature sets sufficiently unique.
To keep with a microservice architecture, services should not share disk storage, but communicate over the docker-internal network via REST.

### Iterating

As noted above, FHIR data stored in the HAPI server is persisted across runs; this allows the developer to generate synthetic data
(a time-consuming process) once while while iterating on other features. 

For development purposes, each service is exposed to the localhost on independent ports (applied automatically via `app/docker-compose.override.yaml`):

- router: localhost:80
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

    - This should only rebuild services that have changed and that are dependent on the service; Dockerfiles have also been designed to maximize use of layer caching for fast rebuilds. If you run into trouble and think caching is or other persistent data are an issue, you can try these more forceful and time-consuming rebuilds:
   
      - `docker compose down --remove-orphans --volumes`
      - `rm -rf hapi/postgres_data/*` (to remove HAPI data)
      - `docker compose build --no-cache --progress=plain` (without a target and cache to force rebuild of all services, with plain logging for surfacing potential build errors)
      - `docker compose up --force-recreate --with-dependencies --renew-anon-volumes --detach` (redeploy app)

1. Restart the services with `docker compose up <service_name>`.

    - Re-upping only the relevant service will cause only it and dependent services that have changed to be re-initialized; you won't have to wait for HAPI or other dependent services to restart. Bringing up an an attached state, with a given target, will only show logs for the specific service (useful for print-debugging).

A common development loop is thus simply `docker compose build --with-dependencies <service_name> && docker compose up <service_name>`, using Ctrl-C and rerunning to effectuate code changes, accessing services directly on their local port for testing (e.g. `http://localhost:8001` for `stat_server_py`).

## Miscellaneous

The `scripts` folder contains a few useful scripts:

- `docker_status.sh`: list various running docker resources
- `docker_clean.sh`: clobber running docker resources (containers, networks, volumes)
- `mimic_fetch_decrypt.sh`: fetch MIMIC IV FHIR data and decrypt it (MIMIC IV access approval required, contact Shawn for password)
- `mimic_sample_push_hapi.py`: pushes a rich subsample of the MIMIC IV FHIR data to the running HAPI server for testing