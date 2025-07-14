from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import os
import subprocess
import tempfile
import shutil

import tempfile, shutil, os, subprocess, json, glob, requests



app = FastAPI()

# redirect / to the api docs
@app.get("/")
def redirect_to_docs():
    """Redirects the root URL to the API documentation."""
    return JSONResponse(status_code=307, content={"message": "Redirecting to /docs for API documentation."}, headers={"Location": "/docs"})


def run_synthea(num_patients, num_years):
    """ Runs Synthea to generate synthetic patient data.
    Args:        num_patients: Number of synthetic patients to generate.
        num_years: Number of years of history to generate for each patient.
    Returns:
        A tuple (temp_dir, fhir_dir) where:
        - temp_dir: Temporary directory where Synthea output is stored.
        - fhir_dir: Directory containing the generated FHIR resources.
    Raises:
        Exception: If the Synthea output directory is not found."""
    
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



def fetch_group_by_id(hapi_url, cohort_id):
    """ Fetches a FHIR Group resource by its ID from the HAPI FHIR server."""
    url = f"{hapi_url.rstrip('/')}/Group/{cohort_id}"
    try:
        r = requests.get(url, headers={"Accept": "application/fhir+json"})
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return None
        else:
            r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Error fetching Group/{cohort_id}: {e}")


def merge_group_members(existing_group, new_patient_ids):
    """
    Merges new patient IDs into an existing Group resource's member list.
    """
    # Existing member patient IDs
    existing_member_ids = set()
    for member in existing_group.get("member", []):
        ref = member.get("entity", {}).get("reference", "")
        if ref.startswith("Patient/"):
            existing_member_ids.add(ref.split("/", 1)[1])
    # Merge with new patients
    all_ids = existing_member_ids | set(new_patient_ids)
    # Replace the member array with merged list
    existing_group["member"] = [{"entity": {"reference": f"Patient/{pid}"}} for pid in all_ids]
    return existing_group



def post_bundle(json_file, hapi_url, tags: dict[str, str] = None): # returns (success (bool), message (str), patient_ids (set of str) or None)
    """ Posts a FHIR Bundle or resource to the HAPI FHIR server. Returned patient_ids is a set of patient IDs found in the bundle, useful for cohort management.
    Args:
        json_file: Path to the JSON file containing the FHIR Bundle or resource.
        hapi_url: Base URL of the HAPI FHIR server (e.g., http://hapi:8080/fhir).
        tags: Optional dictionary of tags to apply to the resource or bundle.
    Returns:
        A tuple (success, message, patient_ids) where:
        - success (bool): True if the post was successful, False otherwise.
        - message (str): Response text or error message.
        - patient_ids (set of str): Set of patient IDs found in the bundle, or None if no patients were found.
    """
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
    

def upsert_group(hapi_url, cohort_id, new_patient_ids, tags):
    """ Upserts a FHIR Group resource with the given cohort ID and patient IDs.
    If the Group already exists, it merges the new patient IDs with existing members.
    Args:
        hapi_url: Base URL of the HAPI FHIR server (e.g., http://hapi:8080/fhir).
        cohort_id: The ID of the cohort to create or update.
        new_patient_ids: A set of new patient IDs to add to the Group.
        tags: Optional dictionary of tags to apply to the Group resource.
    Returns:
        The response text from the HAPI FHIR server after the upsert operation.
    Raises:
        RuntimeError: If there is an error fetching or updating the Group resource."""
    # Try to fetch existing Group
    url = f"{hapi_url.rstrip('/')}/Group/{cohort_id}"
    existing_ids = set()
    try:
        r = requests.get(url, headers={"Accept": "application/fhir+json"})
        if r.status_code == 200:
            group = r.json()
            for member in group.get("member", []):
                ref = member.get("entity", {}).get("reference", "")
                if ref.startswith("Patient/"):
                    existing_ids.add(ref.split("/", 1)[1])
        elif r.status_code != 404:
            r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Error fetching Group/{cohort_id}: {e}")

    # Merge new and existing patient ids
    all_ids = existing_ids | set(new_patient_ids)

    group = {
        "resourceType": "Group",
        "id": cohort_id,
        "type": "person",
        "actual": True,
        "member": [{"entity": {"reference": f"Patient/{pid}"}} for pid in all_ids],
        "meta": {
            "tag": [
                {"system": "urn:charm:cohort", "code": cohort_id},
                {"system": "urn:charm:datatype", "code": "synthetic"},
                {"system": "urn:charm:source", "code": "synthea"}
            ]
        }
    }
    if tags:
        apply_tags(group, tags)
    r = requests.put(url, json=group, headers={"Content-Type": "application/fhir+json"})
    r.raise_for_status()
    return r.text


@app.post("/synthetic-patients")
def push_patients(num_patients: int = 10, num_years: int = 1, cohort_id: str = "default"):
    """ Pushes synthetic patient data generated by Synthea to a HAPI FHIR server.
    Args:
        num_patients: Number of synthetic patients to generate (default is 10).
        num_years: Number of years of history to generate for each patient (default is 1).
        cohort_id: Optional ID for the cohort to which these patients belong. If provided, a FHIR Group resource will be created or updated with these patients.
    Returns:
        A summary of the operation including successful and failed bundles, patient IDs, and tags applied.
    """
    if num_patients <= 0:
        return JSONResponse(status_code=400, content={"error": "num_patients must be a positive integer."})
    if num_years <= 0:
        return JSONResponse(status_code=400, content={"error": "num_years must be a positive integer."})

    hapi_url = "http://hapi:8080/fhir"
    # we need to check if the hapi server is running by checking fhir/$meta, return an error if result is not 200; no retries
    try:
        r = requests.get(hapi_url + "/$meta")
        r.raise_for_status()
    except Exception as e:
        # we'll return a 500 error with the messag se
        ret = JSONResponse(status_code=500, content={"error": f"HAPI FHIR server is not reachable. (It may be starting up.)"})
        return ret

    temp_dir, fhir_dir = run_synthea(num_patients, num_years)

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


        try:
            msg = upsert_group(hapi_url, cohort_id, patient_ids, tagset)
            results.append({"file": f"group_{cohort_id}", "success": True, "msg": msg})
        except Exception as e:
            results.append({"file": f"group_{cohort_id}", "success": False, "msg": str(e)})

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

