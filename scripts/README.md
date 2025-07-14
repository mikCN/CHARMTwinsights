

## Build Docker Images

First, build the images for the application:

```bash
# working dir: app
docker compose build --with-dependencies router
```

If you have having trouble, you might add a `--no-cache` to force rebuilding images from scratch, and/or a `--progress plain` to see complete build progress.

Next, build the default images for the model-hosting service. These default models may be complemented with other Docker-based models via the API, provided the referenced images are on the same host as the app, or (in theory) available on Dockerhub or another container registry.

```bash
# working dir: app
model_server/models/build_model_images.sh
```

You can add build args to this script, e.g. `--no-cache` to force rebuilding.

## Start App

Using `docker compose`:

```bash
# working dir: app
docker compose up --detach router
```

If you're having trouble, you may want to add a `--force-recreate`. The API endpoints will be available at `http://localhost/docs`.

For development purposes, the HAPI FHIR server is exposed at `http://localhost:8080`.

## Load Models

TODO: make a separate section for modeling, show prediction
(it's a bit strange, because we may end up putting some of the models as first-class for synthetic data generation under /synthetic/. Maybe at the end of the day we won't expose 
the modeling endpoint publicly but wrap it?)

Register the default predictive models:

```bash
# working dir: app
model_server/models/register_model_images.sh
```

Each model will be tested with the example inputs, returning the generated results. Additional models may be loaded via the `http://localhost/modeling/model` API; see the [TODO MODEL FORMAT README](...) for details on compiling and registering additional models.


## Generate Synthetic Data

Synthetic patient data in FHIR format may be generated via a POST request to http://localhost/synthetic/synthea/generate-synthetic-patients, with url parameters `num_patients`, `num_years`, 
and `cohort_id`. The patients will be simulated with Synthea, and their records will be tagged with the provided `cohort_id` (defaulting to `default`).

It is possible to re-use the same cohort ID across multiple generations, in which case newly generated patients will be added to the cohort.

A testing script demonstrates this, creating a `cohort1` with 6 members, and a `cohort2` with 3. Each generation takes a few seconds.

```bash
# working dir: app
synthea_server/gen_patients.sh
```

These data are pushed to the FHIR server accessible at `http://localhost:8080` for development purposes.
