from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from the synthea python server!"}

## ok, so we want to provide an endpoint that returns a list of synthetic patients
# the general form for the call to synthea is:
# https://github.com/synthetichealth/synthea/blob/master/src/main/resources/synthea.properties
# CMD rm -rf synthea_output/* && \
#     java -jar synthea-with-dependencies.jar \
#         -d modules \
#         --exporter.baseDirectory synthea_output \
#         --exporter.fhir.use_us_core_ig true \
#         -p ${NUM_PATIENTS} \
#         --exporter.years_of_history ${NUM_YEARS} \
#         ${EXTRA_ARGS} \
#         --exporter.csv.export true

# if if use the fhir exporter, we get a directory of json files; if we use the csv exporter, we get a directory of csv files:
# synthea_output/csv:
# allergies.csv           claims_transactions.csv encounters.csv          medications.csv         patients.csv            procedures.csv
# careplans.csv           conditions.csv          imaging_studies.csv     observations.csv        payer_transitions.csv   providers.csv
# claims.csv              devices.csv             immunizations.csv       organizations.csv       payers.csv              supplies.csv

# synthea_output/fhir:
# Amiee221_Evelina828_Reichel38_9206ece0-c878-d223-002f-b5189a519710.json     Lavern240_Treutel973_7353e17f-0cd5-5b0a-c736-92b9ca5f8366.json
# Cordie578_Kelsey155_Gusikowski974_069b5064-ff05-2225-3995-f32685518bc6.json Lecia978_Lizabeth515_Boehm581_347ceebf-0248-5a56-14f3-e1e8e8ffb73c.json
# Dennise990_Rath779_79590754-4679-dafd-8aab-103706580fff.json                hospitalInformation1744134592251.json
# Jessie665_Glover433_1e621f4c-db30-c273-49e9-2dcad508a9cb.json               practitionerInformation1744134592251.json

# params we want to support in the API:
# - num_patients: number of patients to generate
# - num_years: number of years of history to generate
# - extra_args: any extra args to pass to synthea
# - exporter: the exporter to use (csv or fhir)
# the return value will be a zip file with the generated patients
# we also want to make sure it doesn't take too long to generate patients (10 seconds), and that the output is limited to 10 megabytes

# example call: GET http://localhost:8000/synthetic-patients?num_patients=10&num_years=1&extra_args="--exporter.fhir.use_us_core_ig true"&exporter=csv
@app.get("/synthetic-patients")
def get_patients(num_patients: int = 10, num_years: int = 1, exporter: str = "csv"):
    import os
    import subprocess
    import tempfile  # (unused after edit)
    import re
    import shutil
    import zipfile
    import asyncio

    # check if the exporter is valid
    if exporter not in ["csv", "fhir"]:
        return JSONResponse(status_code=400, content={"error": "Invalid exporter. Must be 'csv' or 'fhir'."})
    # check if the number of patients is valid
    if num_patients <= 0:
        return JSONResponse(status_code=400, content={"error": "Number of patients must be greater than 0."})
    # check if the number of years is valid
    if num_years <= 0:
        return JSONResponse(status_code=400, content={"error": "Number of years must be greater than 0."})
    
    async def run_synthea(num_patients, num_years, exporter):
        # create or find the next numbered cohort directory in ../../syn_cohorts
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        # Find all subdirectories that are just numbers
        existing = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and re.fullmatch(r'\d+', d)]
        next_num = 1
        if existing:
            max_num = max(int(d) for d in existing)
            next_num = max_num + 1
        cohort_number = next_num
        cohort_dir = os.path.join(base_dir, str(cohort_number))
        os.makedirs(cohort_dir, exist_ok=False)  # fail if already exists, should not happen

        # run synthea
        cmd = [
            "java",
            "-jar",
            "synthea-with-dependencies.jar",
            "-d",
            "modules",
            "--exporter.baseDirectory",
            cohort_dir,
            "-p",
            str(num_patients),
            "--exporter.years_of_history",
            str(num_years),
        ]
        # if exporter == "csv":
        cmd.append("--exporter.csv.export")
        cmd.append("true")
        #elif exporter == "fhir":
        cmd.append("--exporter.fhir.use_us_core_ig")
        cmd.append("true")
        subprocess.run(cmd, check=True)

        # zip up the cohort folder into syn_cohorts as cohort-{cohort_number}.zip
        zip_file = os.path.join(base_dir, f"cohort-{cohort_number}.zip")
        with zipfile.ZipFile(zip_file, 'w') as zf:
            for root, dirs, files in os.walk(cohort_dir):
                for file in files:
                    if file.endswith(".csv") or file.endswith(".json"):
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), cohort_dir))

        # check the size of the zip file (optional, not enforced)
        zip_size = os.path.getsize(zip_file)
        #if zip_size > 10 * 1024 * 1024:
            # return an error message as a string
            #return "Error: Zip file is too large. Maximum size is 10 MB."

        # return both the path to the zip file and the cohort folder
        return zip_file, cohort_dir

    # run the synthea command in a separate thread so it doesn't block the main thread and we can enforce the timeout
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    #try:
    result = loop.run_until_complete(asyncio.wait_for(run_synthea(num_patients, num_years, exporter), timeout=10))
    print("RESULT:", result)
    # check if the result is an error message; indicated by a string beginning with "Error:"
    if isinstance(result, str) and result.startswith("Error:"):
        response =  JSONResponse(status_code=500, content={"error": result})
    else:
        zip_path, cohort_dir = result
        def iterfile():
            with open(zip_path, 'rb') as f:
                yield from f

        response = StreamingResponse(iterfile(), media_type="application/zip")
        response.headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_path)}"'
        # Do not delete the cohort folder; keep both the folder and the zip file
    return response
    # except subprocess.CalledProcessError as e:
    #     return JSONResponse(status_code=500, content={"error": f"Error running synthea: {e}"})
    # except asyncio.TimeoutError:
    #     return JSONResponse(status_code=500, content={"error": "Error: Synthea took too long to run."})
    # except Exception as e:
    #     return JSONResponse(status_code=500, content={"error": f"Error: {e}"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# UNIQUE_IDENTIFIER_1751817569
