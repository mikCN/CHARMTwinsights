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
def get_patients(
    num_patients: int = 10,
    num_years: int = 1,
    exporter: str = "csv",
    min_age: int = 0,
    max_age: int = 140,
    gender: str = "both",
    state: str = None,
    download_zip: bool = True
):
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
    
    async def run_synthea(num_patients, num_years, exporter, min_age, max_age, gender, state):
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

        # Handle age
        if min_age != 0 or max_age != 140:
            cmd.extend(["-a", f"{min_age}-{max_age}"])

        # Handle gender
        gender_norm = gender.strip().lower()
        gender_arg = None
        if gender_norm in ["m", "male"]:
            gender_arg = "M"
        elif gender_norm in ["f", "female"]:
            gender_arg = "F"
        # Only add -g if gender is not 'both'
        if gender_arg:
            cmd.extend(["-g", gender_arg])

        if exporter == "csv":
            cmd.append("--exporter.csv.export")
            cmd.append("true")
        elif exporter == "fhir":
            cmd.append("--exporter.fhir.use_us_core_ig")
            cmd.append("true")

        # Handle state (as positional argument at the end)
        if state:
            cmd.append(state)

        subprocess.run(cmd, check=True)

        zip_file = None
        if download_zip:
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

        # return both the path to the zip file (if created) and the cohort folder
        return zip_file, cohort_dir

    # run the synthea command in a separate thread so it doesn't block the main thread and we can enforce the timeout
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    #try:
    result = loop.run_until_complete(asyncio.wait_for(run_synthea(num_patients, num_years, exporter, min_age, max_age, gender, state), timeout=30))
    print("RESULT:", result)
    # check if the result is an error message; indicated by a string beginning with "Error:"
    if isinstance(result, str) and result.startswith("Error:"):
        response =  JSONResponse(status_code=500, content={"error": result})
    else:
        zip_path, cohort_dir = result
        if download_zip and zip_path:
            def iterfile():
                with open(zip_path, 'rb') as f:
                    yield from f
            response = StreamingResponse(iterfile(), media_type="application/zip")
            response.headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_path)}"'
        else:
            response = JSONResponse(status_code=200, content={"message": "Cohort generated and stored.", "cohort_dir": cohort_dir})
        # Do not delete the cohort folder; keep both the folder and the zip file
    return response
    # except subprocess.CalledProcessError as e:
    #     return JSONResponse(status_code=500, content={"error": f"Error running synthea: {e}"})
    # except asyncio.TimeoutError:
    #     return JSONResponse(status_code=500, content={"error": "Error: Synthea took too long to run."})
    # except Exception as e:
    #     return JSONResponse(status_code=500, content={"error": f"Error: {e}"})


from fastapi import Path
from fastapi.responses import StreamingResponse

@app.get("/download-cohort-zip/{cohort_id}")
def download_cohort_zip(cohort_id: int = Path(..., description="The cohort number to download as zip")):
    import os
    import zipfile

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
    zip_path = os.path.join(base_dir, f"cohort-{cohort_id}.zip")
    cohort_dir = os.path.join(base_dir, str(cohort_id))

    if os.path.exists(zip_path):
        def iterfile():
            with open(zip_path, 'rb') as f:
                yield from f
        return StreamingResponse(iterfile(), media_type="application/zip", headers={
            'Content-Disposition': f'attachment; filename="cohort-{cohort_id}.zip"'
        })
    elif os.path.exists(cohort_dir) and os.path.isdir(cohort_dir):
        # Create zip file
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for root, dirs, files in os.walk(cohort_dir):
                for file in files:
                    if file.endswith(".csv") or file.endswith(".json"):
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), cohort_dir))
        def iterfile():
            with open(zip_path, 'rb') as f:
                yield from f
        return StreamingResponse(iterfile(), media_type="application/zip", headers={
            'Content-Disposition': f'attachment; filename="cohort-{cohort_id}.zip"'
        })
    else:
        return JSONResponse(status_code=404, content={"error": f"No zip or cohort folder found for cohort {cohort_id}"})





@app.get("/cohort-metadata/{cohort_id}")
def get_cohort_metadata(cohort_id: int = Path(..., description="The cohort number to get metadata for")):
    import os
    import json
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
    cohort_dir = os.path.join(base_dir, str(cohort_id))
    metadata_dir = os.path.join(cohort_dir, "metadata")
    if not os.path.exists(cohort_dir) or not os.path.isdir(cohort_dir):
        return JSONResponse(status_code=404, content={"error": f"Cohort folder {cohort_id} not found."})
    if not os.path.exists(metadata_dir) or not os.path.isdir(metadata_dir):
        return JSONResponse(status_code=404, content={"error": f"Metadata folder not found for cohort {cohort_id}."})
    # Find the first .json file in the metadata directory
    json_files = [f for f in os.listdir(metadata_dir) if f.endswith('.json')]
    if not json_files:
        return JSONResponse(status_code=404, content={"error": f"No metadata JSON file found for cohort {cohort_id}."})
    metadata_path = os.path.join(metadata_dir, json_files[0])
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        return JSONResponse(status_code=200, content=metadata)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Could not read metadata: {str(e)}"})





@app.get("/cohort-metadata-all")
def get_all_cohort_metadata():
    import os
    import json
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
    if not os.path.exists(base_dir) or not os.path.isdir(base_dir):
        return JSONResponse(status_code=200, content=[])
    cohort_numbers = [d for d in os.listdir(base_dir) if d.isdigit() and os.path.isdir(os.path.join(base_dir, d))]
    cohort_numbers = sorted([int(n) for n in cohort_numbers], reverse=True)
    all_metadata = []
    for cohort_id in cohort_numbers:
        metadata_dir = os.path.join(base_dir, str(cohort_id), "metadata")
        if os.path.exists(metadata_dir) and os.path.isdir(metadata_dir):
            json_files = [f for f in os.listdir(metadata_dir) if f.endswith('.json')]
            if json_files:
                metadata_path = os.path.join(metadata_dir, json_files[0])
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    # Optionally add cohort_id to metadata
                    metadata['cohort_id'] = cohort_id
                    all_metadata.append(metadata)
                except Exception:
                    continue
    return JSONResponse(status_code=200, content=all_metadata)


@app.get("/cohort-attributes-histogram/{cohort_id}")
def cohort_attributes_histogram(cohort_id: int = Path(..., description="The cohort number to calculate attributes histogram for")):
    import os
    import json
    from collections import Counter
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
    cohort_dir = os.path.join(base_dir, str(cohort_id))
    # Try both CSV ('patients') and FHIR ('fhir') patient folders
    if not os.path.exists(cohort_dir) or not os.path.isdir(cohort_dir):
        return JSONResponse(status_code=404, content={"error": f"Cohort folder {cohort_id} not found."})
    candidates = [os.path.join(cohort_dir, "patients"), os.path.join(cohort_dir, "fhir")]
    data_dir = None
    patient_files = []
    for candidate in candidates:
        if os.path.exists(candidate) and os.path.isdir(candidate):
            json_files = [f for f in os.listdir(candidate) if f.endswith('.json')]
            if json_files:
                data_dir = candidate
                patient_files = json_files
                break
    if not data_dir or not patient_files:
        return JSONResponse(status_code=404, content={"error": f"No patient JSON files found for cohort {cohort_id} (checked both 'patients' and 'fhir' folders)."})
    from collections import defaultdict
    # For each key-chain: track total count, set of unique patients, and atomic values for top 3
    key_count = defaultdict(int)
    key_patients = defaultdict(set)
    key_atomic_values = defaultdict(list)

    def walk(obj, prefix=None, patient_id=None):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_prefix = f"{prefix}.{k}" if prefix else k
                key_count[new_prefix] += 1
                if patient_id is not None:
                    key_patients[new_prefix].add(patient_id)
                walk(v, new_prefix, patient_id)
        elif isinstance(obj, list):
            for entry in obj:
                walk(entry, prefix, patient_id)
        else:
            # atomic value
            if prefix is not None:
                val = str(obj)
                if len(val) > 40:
                    val = val[:40] + '...'
                key_atomic_values[prefix].append(val)

    for pf in patient_files:
        try:
            with open(os.path.join(data_dir, pf), 'r') as f:
                data = json.load(f)
            walk(data, prefix=None, patient_id=pf)
        except Exception:
            continue
    result = {}
    for k in key_count:
        total_count = key_count[k]
        unique_patient_count = len(key_patients[k])
        atomic_vals = key_atomic_values.get(k)
        line = f"total: {total_count} - unique patients: {unique_patient_count}"
        if atomic_vals:
            top_3 = Counter(atomic_vals).most_common(3)
            for idx, (val, cnt) in enumerate(top_3, 1):
                line += f" - {idx}st most common: {val}, {cnt}" if idx == 1 else (f" - {idx}nd most common: {val}, {cnt}" if idx == 2 else f" - {idx}rd most common: {val}, {cnt}")
        result[k] = line
    return JSONResponse(status_code=200, content=result)


from fastapi import Query
from fastapi.responses import StreamingResponse
import io
import matplotlib.pyplot as plt

@app.get("/cohort-attribute-visualization/{cohort_id}")
def cohort_attribute_visualization(
    cohort_id: int = Path(..., description="The cohort number to visualize attribute for"),
    key_chain: str = Query(..., description="Dot-separated key chain, e.g., a.b.c or age")
):
    import os
    import json
    from collections import Counter
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
    cohort_dir = os.path.join(base_dir, str(cohort_id))
    # Try both CSV ('patients') and FHIR ('fhir') patient folders
    candidates = [os.path.join(cohort_dir, "patients"), os.path.join(cohort_dir, "fhir")]
    data_dir = None
    patient_files = []
    for candidate in candidates:
        if os.path.exists(candidate) and os.path.isdir(candidate):
            json_files = [f for f in os.listdir(candidate) if f.endswith('.json')]
            if json_files:
                data_dir = candidate
                patient_files = json_files
                break
    if not data_dir or not patient_files:
        return JSONResponse(status_code=404, content={"error": f"No patient JSON files found for cohort {cohort_id} (checked both 'patients' and 'fhir' folders)."})
    # Traverse each file and extract values for the key_chain
    def extract_values(obj, keys):
        if not keys:
            return [obj]
        k = keys[0]
        rest = keys[1:]
        values = []
        if isinstance(obj, dict):
            if k in obj:
                values.extend(extract_values(obj[k], rest))
        elif isinstance(obj, list):
            for entry in obj:
                values.extend(extract_values(entry, keys))
        return values
    keys = key_chain.split('.')
    value_counter = Counter()
    unique_patient_counter = Counter()
    for pf in patient_files:
        try:
            with open(os.path.join(data_dir, pf), 'r') as f:
                data = json.load(f)
            vals = extract_values(data, keys)
            str_vals = [str(v) for v in vals if v is not None]
            value_counter.update(str_vals)
            for v in set(str_vals):
                unique_patient_counter[v] += 1
        except Exception:
            continue
    if not value_counter:
        return JSONResponse(status_code=404, content={"error": f"No values found for key chain '{key_chain}' in cohort {cohort_id}."})
    # Prepare data for both charts
    items = value_counter.most_common(20)  # Show up to 20 most common
    labels, counts = zip(*items)
    unique_counts = [unique_patient_counter[label] for label in labels]
    # Adjust figure height based on number of labels
    fig_height = max(6, 0.5 * len(labels))
    fig, axs = plt.subplots(1, 2, figsize=(18, fig_height), sharey=True)
    # Left: entry count
    axs[0].barh(labels, counts, color='skyblue')
    axs[0].set_ylabel(key_chain)
    axs[0].set_xlabel('Entry Count')
    axs[0].set_title('Entry Count')
    for i, v in enumerate(counts):
        axs[0].text(v, i, str(v), va='center', ha='left', fontsize=10)
    # Right: unique patient count
    axs[1].barh(labels, unique_counts, color='seagreen')
    axs[1].set_xlabel('Unique Patient Count')
    axs[1].set_title('Unique Patient Count')
    for i, v in enumerate(unique_counts):
        axs[1].text(v, i, str(v), va='center', ha='left', fontsize=10)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/cohort-attribute-dot-matrix/{cohort_id}")
def cohort_attribute_dot_matrix(
    cohort_id: int = Path(..., description="The cohort number to visualize attribute matrix for"),
    key_chain_1: str = Query(..., description="Dot-separated key chain for X axis"),
    key_chain_2: str = Query(..., description="Dot-separated key chain for Y axis")
):
    import os
    import json
    from collections import Counter, defaultdict
    import numpy as np
    import matplotlib.pyplot as plt
    import io
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../syn_cohorts'))
    cohort_dir = os.path.join(base_dir, str(cohort_id))
    candidates = [os.path.join(cohort_dir, "patients"), os.path.join(cohort_dir, "fhir")]
    data_dir = None
    patient_files = []
    for candidate in candidates:
        if os.path.exists(candidate) and os.path.isdir(candidate):
            json_files = [f for f in os.listdir(candidate) if f.endswith('.json')]
            if json_files:
                data_dir = candidate
                patient_files = json_files
                break
    if not data_dir or not patient_files:
        return JSONResponse(status_code=404, content={"error": f"No patient JSON files found for cohort {cohort_id} (checked both 'patients' and 'fhir' folders)."})
    def extract_value(obj, keys):
        if not keys:
            return [obj]
        k = keys[0]
        rest = keys[1:]
        values = []
        if isinstance(obj, dict):
            if k in obj:
                values.extend(extract_value(obj[k], rest))
        elif isinstance(obj, list):
            for entry in obj:
                values.extend(extract_value(entry, keys))
        return values
    keys1 = key_chain_1.split('.')
    keys2 = key_chain_2.split('.')
    pair_counter = Counter()
    pair_to_patients = defaultdict(set)
    for pf in patient_files:
        try:
            with open(os.path.join(data_dir, pf), 'r') as f:
                data = json.load(f)
            vals1 = extract_value(data, keys1)
            vals2 = extract_value(data, keys2)
            for v1 in vals1:
                for v2 in vals2:
                    if v1 is not None and v2 is not None:
                        pair_counter[(str(v1), str(v2))] += 1
                        pair_to_patients[(str(v1), str(v2))].add(pf)
        except Exception:
            continue
    if not pair_counter:
        return JSONResponse(status_code=404, content={"error": f"No value pairs found for the given key chains in cohort {cohort_id}."})
    # Prepare data for plotting
    x_labels = sorted(set([k[0] for k in pair_counter.keys()]))
    y_labels = sorted(set([k[1] for k in pair_counter.keys()]))
    x_idx = {v: i for i, v in enumerate(x_labels)}
    y_idx = {v: i for i, v in enumerate(y_labels)}
    xs, ys, sizes, sizes_unique = [], [], [], []
    for (v1, v2), count in pair_counter.items():
        xs.append(x_idx[v1])
        ys.append(y_idx[v2])
        sizes.append(count * 40)  # scale dot size by entry count
        sizes_unique.append(len(pair_to_patients[(v1, v2)]) * 40)  # scale dot size by unique patient count
    fig_height = max(6, 0.5 * len(y_labels))
    fig_width = max(14, 0.7 * len(x_labels))
    fig_height = max(10, 0.7 * len(y_labels) * 2)
    fig, axs = plt.subplots(2, 1, figsize=(fig_width, fig_height), sharex=True)
    # Plot 1: Entry count (top)
    scatter1 = axs[0].scatter(xs, ys, s=sizes, alpha=0.7, color='royalblue', edgecolors='black')
    axs[0].set_xticks(range(len(x_labels)))
    axs[0].set_xticklabels(x_labels, rotation=45, ha='right', fontsize=10)
    axs[0].set_yticks(range(len(y_labels)))
    axs[0].set_yticklabels(y_labels, fontsize=12)
    axs[0].set_ylabel(key_chain_2, fontsize=13)
    axs[0].set_title("Entry Count", fontsize=14)
    axs[0].tick_params(axis='y', labelsize=12, pad=10)
    # Plot 2: Unique patient count (bottom)
    scatter2 = axs[1].scatter(xs, ys, s=sizes_unique, alpha=0.7, color='seagreen', edgecolors='black')
    axs[1].set_xticks(range(len(x_labels)))
    axs[1].set_xticklabels(x_labels, rotation=45, ha='right', fontsize=10)
    axs[1].set_yticks(range(len(y_labels)))
    axs[1].set_yticklabels(y_labels, fontsize=12)
    axs[1].set_ylabel(key_chain_2, fontsize=13)
    axs[1].set_xlabel(key_chain_1, fontsize=13)
    axs[1].set_title("Unique Patient Count", fontsize=14)
    axs[1].tick_params(axis='y', labelsize=12, pad=10)
    plt.subplots_adjust(left=0.25, hspace=0.3, bottom=0.15)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
