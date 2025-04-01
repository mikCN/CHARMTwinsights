SHELL := /bin/bash
.PHONY: poetry-install

# install deps and fetch synthea jar
install: poetry-install fetch-synthea-jar

fetch-synthea-jar:
	curl -L -o synthea/synthea-with-dependencies.jar https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar

poetry-install:
	poetry install

# build some patients with synthea
regen-patients:
	# some additional synthea options https://github.com/synthetichealth/synthea/blob/master/src/main/resources/synthea.properties
	# tested with openjdk 23.0.2 (installed via homebrew, OSX), recent version required to get clinical notes and text export

	rm -rf synthea/output/*

	java -jar synthea/synthea-with-dependencies.jar -p 20 -a 1-90 -s 123 \
	   -d synthea/modules \
	   --exporter.baseDirectory synthea/output \
	   --exporter.fhir.use_us_core_ig true \
	   --physiology.generators.enabled true \
	   --physiology.state.enabled true \
	   --exporter.csv.export true

	   # I don't know if the physiology ones above do anything?
	   # other flags of possible interest:
	   #--exporter.clinical_note.export true	
	   #--exporter.text.export true \
	   #--exporter.fhir.bulk_data true \
	   #--exporter.subfolders_by_id_substring true \

# start the hapi server - wait a few mins for it to come up before trying to ingest
hapi-up:
	# https://github.com/hapifhir/hapi-fhir-jpaserver-starter/blob/master/src/main/resources/application.yaml
	docker run -d -p 8080:8080 \
	    hapiproject/hapi:latest

		# this appears to just be for loading .ndjson files from the web via provided URLs, not bulk-from-post requests
		#-e hapi.fhir.bulk_import_enabled=true \

		# attempts at optimizing for faster loading.... nothing seems to help much
		#-e hapi.fhir.allow_deletes=false \
		#-e hapi.fhir.reuse_cached_search_results_millis=-1 \
		#-e hapi.fhir.retain_cached_searches_mins=-1 \
		#-e hapi.fhir.expunge_enabled=false \
		#-e hapi.fhir.delete_expunge_enabled=false \

# stop and remove hapi server container - data will be lost
hapi-down:
	docker stop $(shell docker ps -q --filter ancestor=hapiproject/hapi:latest)

# show the hapi server logs
hapi-logs:
	docker logs $(shell docker ps -q --filter ancestor=hapiproject/hapi:latest)

# ingest data into hapi server
hapi-ingest-patients:
	poetry run python scripts/fhir_upload_script.py
