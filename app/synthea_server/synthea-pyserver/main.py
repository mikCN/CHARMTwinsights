from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import os
import subprocess
import tempfile
import shutil

import tempfile, shutil, os, subprocess, json, glob, requests



app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from the synthea python server!"}


def run_synthea(num_patients, num_years, exporter):
    temp_dir = tempfile.mkdtemp()
    cmd = [
        "java", "-jar", "synthea-with-dependencies.jar",
        "-d", "modules",
        "--exporter.baseDirectory", temp_dir,
        "-p", str(num_patients),
        "--exporter.years_of_history", str(num_years),
        "--exporter.fhir.export", "true"
    ]
    print(cmd)
    subprocess.run(cmd, check=True)
    fhir_dir = os.path.join(temp_dir, "fhir")
    if not os.path.isdir(fhir_dir):
        raise Exception("FHIR output directory not found!")
    return temp_dir, fhir_dir

# tags are organized as system: code, like {"urn:charm:cohort": "cohortA", "urn:charm:datatype": "synthetic"}

# input could be a resource or a bundle
# both resources and bundles should have a "meta" field and tags applied
# bundles can contain resources or bundles, so we need to work recursively
# tags are of the form system: code, e.g. {"urn:charm:cohort": "cohortA", "urn:charm:datatype": "synthetic"}
def apply_tags(resource, tags: dict[str, str] = None):
    """
    Recursively applies FHIR tags (in meta.tag) to all resources in a bundle or a single resource.
    Args:
        resource: dict representing a FHIR resource (could be Bundle or any resource)
        tags: dict of {system: code} to apply as tags
    """
    if tags is None:
        tags = {}

    # --- Step 1: Add tags to this resource's meta ---
    meta = resource.setdefault("meta", {})
    meta_tags = meta.setdefault("tag", [])

    # Index existing tags by system for easy update
    tag_index = {t["system"]: t for t in meta_tags if "system" in t and "code" in t}

    # Apply or update each tag
    for system, code in tags.items():
        if system in tag_index:
            tag_index[system]["code"] = code
        else:
            meta_tags.append({
                "system": system,
                "code": code
            })

    # --- Step 2: Recurse if this is a bundle ---
    if resource.get("resourceType") == "Bundle":
        for entry in resource.get("entry", []):
            entry_resource = entry.get("resource")
            if entry_resource:
                apply_tags(entry_resource, tags)

    # --- Step 3 (optional): Handle contained resources ---
    if "contained" in resource:
        for contained in resource["contained"]:
            apply_tags(contained, tags)



def post_bundle(json_file, hapi_url, tags: dict[str, str] = None): # returns (success (bool), message (str), patient_ids (set of str) or None)
    patient_ids = set()
    with open(json_file, "r") as f:
        bundle = json.load(f)

        # collect patient IDs
        if bundle.get("resourceType") == "Bundle" and "entry" in bundle:
            for entry in bundle["entry"]:
                if "resource" in entry and entry["resource"].get("resourceType") == "Patient":
                    patient_id = entry["resource"].get("id")
                    if patient_id:
                        patient_ids.add(patient_id)
         
        if tags:
            apply_tags(bundle, tags)

    bundle_type = bundle.get("type")
    # Decide endpoint based on bundle type
    if bundle_type in ("transaction", "batch"):
        url = hapi_url  # base URL, e.g. http://hapi:8080/fhir
    else:
        url = hapi_url.rstrip("/") + "/Bundle"
    try:
        r = requests.post(url, json=bundle, headers={"Content-Type": "application/fhir+json"})
        r.raise_for_status()
        return True, r.text, patient_ids
    except requests.HTTPError as e:
        error_body = r.text if 'r' in locals() else str(e)
        return False, error_body, None
    except Exception as e:
        return False, str(e), None
    

def gen_group_resource(cohort_id: str, patient_ids: set[str], tags: dict[str, str] = None) -> dict:
    """
    Generates a FHIR Group resource for the given cohort ID and patient IDs.
    """
    group = {
        "resourceType": "Group",
        "id": cohort_id,
        "type": "person",
        "actual": True,
        "member": [{"entity": {"reference": f"Patient/{pid}"}} for pid in patient_ids],
        "meta": {
            "tag": [
                {"system": "urn:charm:cohort", "code": cohort_id},
                {"system": "urn:charm:datatype", "code": "synthetic"},
                {"system": "urn:charm:source", "code": "synthea"}
            ]
        }
    }
    
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [{
            "fullUrl": f"urn:uuid:{cohort_id}",
            "resource": group,
            "request": {
                "method": "POST",
                "url": "Group"
            }
        }]
    }

    apply_tags(bundle, tags)

    return bundle

@app.post("/synthetic-patients/push")
def push_patients(num_patients: int = 10, num_years: int = 1, cohort_id: str = None):
    hapi_url = "http://hapi:8080/fhir"
    # we need to check if the hapi server is running by checking fhir/$meta, return an error if result is not 200; no retries
    try:
        r = requests.get(hapi_url + "/$meta")
        r.raise_for_status()
    except Exception as e:
        # we'll return a 500 error with the message
        ret = JSONResponse(status_code=500, content={"error": f"HAPI FHIR server is not reachable. (It may be starting up.)"})
        return ret

    temp_dir, fhir_dir = run_synthea(num_patients, num_years, "fhir")


    tagset = None
    if cohort_id:
        tagset = {"urn:charm:cohort": cohort_id, "urn:charm:datatype": "synthetic", "urn:charm:source": "synthea"} 

    try:
        # 1. Practitioner and hospital info first
        special_files = sorted(glob.glob(os.path.join(fhir_dir, "practitionerInformation*.json"))) + \
                        sorted(glob.glob(os.path.join(fhir_dir, "hospitalInformation*.json")))
        all_files = sorted(glob.glob(os.path.join(fhir_dir, "*.json")))
        patient_files = [f for f in all_files if f not in special_files]

        results = []
        # First special files
        for json_file in special_files:
            success, msg, _ = post_bundle(json_file, hapi_url, tags=tagset)
            results.append({"file": os.path.basename(json_file), "success": success, "msg": msg})

        # Then patient bundles
        patient_ids = set()
        for json_file in patient_files:
            success, msg, new_patient_ids = post_bundle(json_file, hapi_url, tags=tagset)
            patient_ids.update(new_patient_ids)
            results.append({"file": os.path.basename(json_file), "success": success, "msg": msg})

        # Now a new group resource contained in a bundle (written to a file for reuse of post_bundle which takes files)
        group_bundle = gen_group_resource(cohort_id, patient_ids, tags=tagset)
        print(group_bundle)
        group_file = os.path.join(temp_dir, f"group_{cohort_id}.json")
        with open(group_file, "w") as f:
            json.dump(group_bundle, f, indent=2)

        success, msg, _ = post_bundle(group_file, hapi_url, tags=tagset)
        print(success, msg)
        results.append({"file": os.path.basename(group_file), "success": success, "msg": msg}) 

        summary = {
            "successful_bundles": sum(1 for r in results if r["success"]),
            "failed_bundles": sum(1 for r in results if not r["success"]), 
            "patient_ids": list(patient_ids),
            "num_patients": len(patient_ids),
            "tags_applied": tagset
        }
        return summary
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

