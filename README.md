# CHARMTwinsight

NOTE: This is a testing branch, attempting to integrate synthea as an API-available part of the main application. This version
does so by running a Python FastAPI service calling out to the java application as a subprocess passing some parameters, returning
a .zip file with contents. There are currently two issues:

1) it is not fully working - something about the return of the .zip file (potentially related to the async-enforced time limit?)
2) it is really slow, requiring a full spin-up of synthea + modules for each generation

Another branch is investigating (even less successfully) the service solution at https://github.com/robcaruso/dhp-synthea-service


## 📌 Overview
This repository provides a **data ingestion pipeline** that loads **synthetic patient data** (generated using [Synthea](https://github.com/synthetichealth/synthea)) into a **HAPI-FHIR server**.
This iteration also hosts (placeholder) **data analytics** services via Python and R in a **microservices** architecture.
# CHARMTwinsight

## 🏥 What is FHIR and HAPI-FHIR?
- **FHIR (Fast Healthcare Interoperability Resources)** is a **standard** for exchanging healthcare data electronically.
- **HAPI-FHIR** is an **open-source implementation** of FHIR, providing a Java-based **FHIR server** for storing and querying patient records.
- CHARMTwinsight **ingests patient data to HAPI-FHIR**, and provides an analytic framework for working with the data.

## 🏗 Repository Structure

This repo is currently organized in 2 stacks, each managed `docker-compose` in conjunction with scripts in the `scripts` folder.

- The `app` directory contains the components that make up the application stack:
  - A HAPI FHIR server, `hapi`, for ingesting and serving FHIR data
    - The `postgres_data` subfolder is used to persistently store ingested FHIR data across server restarts etc.
    - `scripts/hapi_*.sh` provide utilities for working with the server.
  - A `pyserver`, which can make queries to the HAPI server, potentially do analytics, and return results via a `FastAPI` REST API.
    - This subfolder is managed by `poetry`; working in this directory `poetry add` et al. can be used to add dependency packages, interactive (non-docker) development, etc.
    - `scripts/pyserver_*.sh` provide utilities for working with the server; note starting will re-build and re-start if already running.
  - An `rserver`, which can make queries to the HAPI server, potentially do analytics, and return results via a `plumber` REST API.
    - This is a simple R stack; dependencies should be added in the `Dockerfile`. If doing interactive (non-docker) development, you can use regular `install.packages()` et al. in your R session.
    - `scripts/rserver_*.sh` provide utilities for working with the server; note starting will re-build and re-start if already running.
    
- The `tools` directory contains components that aren't part of the application, but useful for development, also managed by `docker-compose` for ease of development. Currently this just consists of dockerized `synthea` for generation of synthetic FHIR data.
  - The `output` folder is meant for outputs, organized by subdirectory (e.g. `tools/output/synthea`)
  - Other utilities in the `scripts` directory are useful here, including `docker_*.sh` (for general docker management) and `synthea_*.sh` for genererating FHIR data and pushing it to the FHIR server.


## ⚙️ Installation & Setup

### 1 Install Dependencies

You will need `docker` and `docker-compose`; if using a Mac install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and `docker-compose` via Homebrew. (TODO: as noted in the [CHARMomics](https://github.com/CHARM-BDF/charmomics) repo docker compose is not integrated with docker desktop, should be an easy swap in the scripts.)

- Mac users may also wish to install GNU versions of [coreutils](https://formulae.brew.sh/formula/coreutils)
- **Mac users may also need to enable Docker volume storage under `System Preferences -> Privacy and Security -> Files and Folders -> Docker`**

### 2 Start Services

You will need at least the HAPI server running; you may also want to run the `rserver` and `pyserver`:

```
scripts/hapi_start.sh
scripts/pyserver_start.sh
scripts/rserver_start.sh
```

These scrips should handle building the required docker images etc.

### 3 Generate Data

You can edit the following script to modify data generation parameters (which are stored as environment variables):

```
scripts/synthea_gen_data.sh
```

Or you can pass those params on the command-line:

```
NUM_YEARS=2 NUM_PATIENTS=10 scripts/synthea_gen_data.sh
```

**NOTE**: For testing purposes, using more than 1 year of data slows down the ingestion into the HAPI server significantly, which is not fast for data ingest.

**NOTE 2**: Currently generating data overwrites any previously generated data present in `tools/output/synthea`.

### 4 Ingest Data

The HAPI server must be running (above):

```
scripts/synthea_push_hapi_data.sh
```

### 5 Try 'Analytic Services'

NOTE: this part is in active development, and much tooling and analytics has not yet been created.

The running `rserver` exposes `/` and `/patients` on `http://localhost:8001`, and the running `pyserver` exposes `/` and `/patients` on `http://localhost:8000`. Currently they just fetch some data from the HAPI server and serve it up via the endpoint. For convenience:

- pyserver / [http://localhost:8000/](http://localhost:8000/)
- pyserver /patients [http://localhost:8000/patients](http://localhost:8000/patients)
- rserver / [http://localhost:8001/](http://localhost:8001/)
- rserver /patients [http://localhost:8001/patients](http://localhost:8001/patients)

### 6 Logging and Cleaning Up

- `*_logs.sh` can be used to see logs from running containers
- `*_stop.sh` stops running containers, but does not clean out any existing stored data (e.g., ingested HAPI patient data)
- `hapi_clean.sh` removes the stored ingested data for the HAPI server; the next `hapi_start.sh` will start with a clean slate.
- `docker_status.sh` is a utility to see which docker containers are running on your system, and which are part of the `app` or `tools` stack.
- `docker_clean.sh` stops and removes all running docker containers and networks. Be careful with this one if you use docker for other purposes!



## 📜 License
This repository is licensed under **MIT License**. See [`LICENSE`](LICENSE) for details.

## 📩 Contact
For questions, reach out via **GitHub Issues** or email **m.esposito@maastrichtuniversity.nl**.
