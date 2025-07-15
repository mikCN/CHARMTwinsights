#!/usr/bin/env python3

import os
import json
import random
import subprocess
import urllib.request
import urllib.error
import sys


# --- Configuration ---

PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()

## Loads FHIR ndjson files from the MIMIC-IV demo dataset
## and posts them to a local HAPI FHIR server.

# the domains (file prefixes) listed in INCLUDE_ALL will be fully loaded first
# and the rest will be sampled to a maximum of MAX_PER_PT_SAMPLE records per patient

LOCATION = os.path.join(PROJECT_ROOT, "scripts/mimic_data/mimic_iv_100pt_demo/fhir")
INCLUDE_ALL = ["Location", "Organization", "Medication", "Patient"]
FHIR_URL = "http://localhost:8080/fhir"
MAX_PER_PT_SAMPLE = 10
MIN_PER_PT_SAMPLE = 2

def put_fhir_resource(resource, resource_type):
    rid = resource.get("id")
    if not rid:
        print(f"⚠️  Resource missing ID, cannot PUT: {resource}")
        return None
    url = f"{FHIR_URL}/{resource_type}/{rid}"
    data = json.dumps(resource).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/fhir+json"}, method="PUT")

    try:
        with urllib.request.urlopen(req) as response:
            return response.status
    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error {e.code} for {resource_type} ID {rid}")
        print(f"↪ Payload: {json.dumps(resource)[:300]}...")
        print(f"↪ Response body: {e.read().decode()[:300]}...")
        return e.code
    except Exception as e:
        print(f"\n❌ Error posting {resource_type}: {e}")
        return None

def parse_ndjson(filepath):
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

def group_by_patient(resources):
    patients = {}
    for resource in resources:
        ref = resource.get("subject", {}).get("reference", "")
        if ref.startswith("Patient/"):
            pid = ref.split("/")[1]
            patients.setdefault(pid, []).append(resource)
    return patients

def print_progress(resource_type, count, total, status):
    sys.stdout.write(f"\r➡ Posting {resource_type:<15} [{count:4d}/{total:4d}]... {status}   ")
    sys.stdout.flush()

def process_file_all(filepath):
    filename = os.path.basename(filepath)
    print(f"\n📄 Full load for: {filename}")

    resources = list(parse_ndjson(filepath))
    total = len(resources)
    for i, resource in enumerate(resources, 1):
        resource_type = resource.get("resourceType")
        if not resource_type:
            continue
        status = put_fhir_resource(resource, resource_type)
        print_progress(resource_type, i, total, status)
    print(f"\n✔ Finished: {filename}")

def process_file_sampled(filepath):
    filename = os.path.basename(filepath)
    print(f"\n📄 Processing (sampled if needed): {filename}")

    all_resources = list(parse_ndjson(filepath))
    grouped = group_by_patient(all_resources)

    if not grouped:
        print("⚠️  No patient references found. Treating as non-patient-scoped and loading all records.")
        sampled = all_resources
    else:
        over_max = 0
        sampled = []
        for pid, entries in grouped.items():
            total = len(entries)
            if total > MAX_PER_PT_SAMPLE:
                over_max += 1
                sample_size = random.randint(MIN_PER_PT_SAMPLE, MAX_PER_PT_SAMPLE)
                sampled.extend(random.sample(entries, sample_size))
            else:
                sampled.extend(entries)

        if over_max == 0:
            print(f"✅ No sampling needed. Loaded all records for {len(grouped)} patients.")
        else:
            print(f"🔀 Sampling between {MIN_PER_PT_SAMPLE} and {MAX_PER_PT_SAMPLE} records for {over_max} patient(s) with >{MAX_PER_PT_SAMPLE}.")

    total = len(sampled)
    for i, resource in enumerate(sampled, 1):
        resource_type = resource.get("resourceType")
        if not resource_type:
            continue
        status = put_fhir_resource(resource, resource_type)
        print_progress(resource_type, i, total, status)
    print(f"\n✔ Done with: {filename}")

def main():
    files = sorted([f for f in os.listdir(LOCATION) if f.endswith(".ndjson")])
    include_all_set = set(INCLUDE_ALL)

    # Step 1: Full-load for include-all
    for f in files:
        name = os.path.splitext(f)[0]
        if name in include_all_set:
            process_file_all(os.path.join(LOCATION, f))

    # Step 2: Sampled loading for all others
    for f in files:
        name = os.path.splitext(f)[0]
        if name not in include_all_set:
            process_file_sampled(os.path.join(LOCATION, f))

if __name__ == "__main__":
    main()
