# CHARMTwinsight

CHARMTwinsight is part of the CHARM suite of tools, focused on health data storage, predictive analytics, and synthetic data generation. 

It is under active development, and currently consists of the following REST API accessible components:

- A [HAPI](https://hapifhir.io/) FHIR server for storage and delivery of health data in the FHIR format.
- [Synthea](https://synthea.mitre.org/) synthetic data generation in FHIR format.
- A model server, providing Docker-based model hosting and predictive services.

Pre-trained models in development for hosting in the model server include [DPCGAN](https://github.com/sunchang0124/dp_cgans) for differentially private synthetic data generation, and a set of [Cox Proportional Hazard](https://lifelines.readthedocs.io/en/latest/fitters/regression/CoxPHFitter.html) models for common disease risk prediction from common comorbidities, trained on [AllOfUs](https://allofus.nih.gov/) EHR data.

Other in-development features include Python [fhiry](https://github.com/dermatologist/fhiry)-based and R [fhircrackr](https://github.com/POLAR-fhiR/fhircrackr)-based R API servers for FHIR-to-tabular conversions and analytics. 

Finally, the development stack supports fetching, subsampling (for efficiency), and loading [MIMIC IV FHIR](https://physionet.org/content/mimiciv/3.1/) data into the HAPI server.

## Repository Structure

- The `scripts` directory contains scripts for building, starting, stopping, and testing the various services and tools.

- The `tools` directory contains components that aren't part of the application, but useful for development. Currently this just consists of Dockerized Synthea for generation of synthetic FHIR data, and `model_server_models` containing some example model definitions for use with the model server.

- The `app` directory contains the components that make up the main application stack, managed by `docker-compose.yml`. 


## ⚙️ Installation & Setup

### 1 Install Dependencies

You will need `docker` and `docker-compose`; if using a Mac install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and `docker-compose` via Homebrew. (TODO: as noted in the [CHARMomics](https://github.com/CHARM-BDF/charmomics) repo docker compose is not integrated with docker desktop, should be an easy swap in the scripts.)

- Mac users may also wish to install GNU versions of [coreutils](https://formulae.brew.sh/formula/coreutils)
- **Mac users may also need to enable Docker volume storage under `System Preferences -> Privacy and Security -> Files and Folders -> Docker`**

### 2 Start Services

Note: the following sections are not fully up to date with the repo organization - stay tuned.

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
