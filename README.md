

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

First, build the images for the application with `docker compose`:

```bash
# working dir: app
docker compose build --with-dependencies router
```

If you have having trouble, you might add a `--no-cache` to force rebuilding images from scratch, and/or a `--progress=plain` to see complete build progress and error logs.

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
docker compose up --detach router
```

This starts the application in a detached state, requring a `docker compose down` to stop the various containers. By default docker compose only starts/restarts containers that are not running or have changed; adding `--force-recreate` forces the removal and recreation. 

The main API endpoints will be browsable at [`http://localhost/docs`](http://localhost/docs). For development purposes, the HAPI FHIR server is also exposed at [`http://localhost:8080`](http://localhost:8080); **This can be used to browse generated FHIR data and run ad-hoc queries.**

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

Predictive model capabilities are accessed at `http://localhost/modeling`. Example CURLs are available via script:

```bash
# working dir: app
model_server/models/test_predict_models.sh
```

### 7. Test Summary Statistics

Summary statistics about generated patient data are available at `http://localhost/stats`. Examples CURs are available via script:

```bash
# working dir: app
stat_server_py/test_stats.sh
```


