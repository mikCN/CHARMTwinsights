`gen_data.sh`: Builds a docker container with the Synthea command-line application and runs it to generate a set of synthetic FHIR records. This not part of the main app, but rather for local development and testing purposes.

`push_hapi_data.sh`: Pushes the generated FHIR data to HAPI; the HAPI FHIR server must be running (see `scripts/hapi`)