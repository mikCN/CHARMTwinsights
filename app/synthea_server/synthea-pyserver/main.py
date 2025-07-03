from fastapi import FastAPI, HTTPException
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import os
import subprocess
import tempfile
import shutil
import zipfile
import asyncio
import logging


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
def get_patients(num_patients: int = 10, num_years: int = 1, exporter: str = "csv", background_tasks: BackgroundTasks = None):

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
        # create a temporary directory to store the output
        temp_dir = tempfile.mkdtemp()
        # run synthea
        cmd = [
            "java",
            "-jar",
            "synthea-with-dependencies.jar",
            "-d",
            "modules",
            "--exporter.baseDirectory",
            temp_dir,
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

        # zip it up
        zip_file = os.path.join(temp_dir, "synthea_output.zip")
        with zipfile.ZipFile(zip_file, 'w') as zf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".csv") or file.endswith(".json"):
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))

        # check the size of the zip file
        zip_size = os.path.getsize(zip_file)
        if zip_size > 100 * 1024 * 1024:
            # return an error message as a string
            return "Error: Zip file is too large. Maximum size is 100 MB."

        # return the path to the zip file
        return zip_file

    # run the synthea command in a separate thread so it doesn't block the main thread and we can enforce the timeout
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    #try:
    result = loop.run_until_complete(asyncio.wait_for(run_synthea(num_patients, num_years, exporter), timeout=10))

    # check if the result is an error message; indicated by a string beginning with "Error:"
    if isinstance(result, str) and result.startswith("Error:"):
        response = JSONResponse(status_code=500, content={"error": result})
    else:
        def iterfile():
            with open(result, 'rb') as f:
                yield from f

        # CLEANUP: use background task to delete after response is sent
        temp_dir = os.path.dirname(result)
        background_tasks.add_task(shutil.rmtree, temp_dir, ignore_errors=True)
        response = StreamingResponse(iterfile(), media_type="application/zip")
        response.headers['Content-Disposition'] = 'attachment; filename="synthea_output.zip"'

    return response





@app.get("/modules", response_class=JSONResponse)
async def get_synthea_modules_list():
    try:
        # Access the shared volume path directly
        modules_path = "modules"
        
        if not os.path.exists(modules_path):
            return {
                "modules": {},
                "count": 0,
                "error": f"Path {modules_path} not found"
            }
        
        # Function to collect JSON files recursively
        def find_json_files(directory):
            json_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.json'):
                        # Get relative path from base modules directory
                        rel_path = os.path.relpath(os.path.join(root, file), modules_path)
                        json_files.append((rel_path, os.path.join(root, file)))
            return json_files
        
        # Get all JSON files recursively
        module_files = find_json_files(modules_path)
        
        # Create a dictionary to store module information
        modules_info = {}
        
        for rel_path, file_path in module_files:
            # Extract information from the JSON file
            try:
                with open(file_path, 'r') as f:
                    import json
                    module_json = json.load(f)
                    
                    module_info = {
                        "name": os.path.basename(file_path),
                        "path": rel_path
                    }
                    
                    # Look for remarks field (case insensitive)
                    remarks = None
                    for key in module_json:
                        if key.lower() == "remarks":
                            remarks = module_json[key]
                            break
                    
                    # If remarks exist, join them if it's a list, otherwise convert to string
                    if isinstance(remarks, list):
                        remarks_text = "\n".join(remarks)
                    elif remarks:
                        remarks_text = str(remarks)
                    else:
                        remarks_text = ""
                    
                    # Check if remarks indicate a blank module or is empty
                    if not remarks_text or "blank module" in remarks_text.lower() or "empty module" in remarks_text.lower():
                        module_info["description"] = "No description provided"
                    else:
                        module_info["description"] = remarks_text
                    
                    # Count states and transitions
                    states_count = 0
                    transitions_count = 0
                    
                    # Count states
                    states = module_json.get("states", {})
                    if isinstance(states, dict):
                        states_count = len(states)
                        
                        # Count transitions by examining each state
                        for state_name, state_data in states.items():
                            # Direct transition
                            if "direct_transition" in state_data:
                                transitions_count += 1
                            
                            # Distributed transition
                            elif "distributed_transition" in state_data:
                                if isinstance(state_data["distributed_transition"], list):
                                    transitions_count += len(state_data["distributed_transition"])
                            
                            # Conditional transition
                            elif "conditional_transition" in state_data:
                                if isinstance(state_data["conditional_transition"], list):
                                    transitions_count += len(state_data["conditional_transition"])
                            
                            # Complex transition
                            elif "complex_transition" in state_data:
                                if isinstance(state_data["complex_transition"], list):
                                    transitions_count += len(state_data["complex_transition"])
                            
                            # Table transition
                            elif "table_transition" in state_data:
                                transitions_count += 1  # Count as one transition since we can't easily count rows
                    
                    module_info["states_count"] = states_count
                    module_info["transitions_count"] = transitions_count
                    
                    # Add module to dictionary with relative path as key
                    # Use rel_path directly as the key
                    modules_info[rel_path] = module_info
                    
            except Exception as e:
                # If we can't read the file, add basic info
                module_info = {
                    "name": os.path.basename(file_path),
                    "path": rel_path,
                    "description": "No description provided",
                    "states_count": 0,
                    "transitions_count": 0,
                    "error": str(e)
                }
                modules_info[rel_path] = module_info
        
        return {
            "modules": modules_info,
            "count": len(modules_info),
            "path": modules_path
        }
        
    except Exception as e:
        logging.error(f"Error accessing modules: {str(e)}", exc_info=True)
        return {
            "modules": {},
            "count": 0,
            "error": str(e)
        }
    
    

@app.get("/modules/{module_name}", response_class=JSONResponse)
async def get_module_content(module_name: str):
    try:
        # Ensure module_name has .json extension
        if not module_name.endswith('.json'):
            module_name += '.json'
            
        # Access the shared volume path directly
        modules_path = "modules"
        
        if not os.path.exists(modules_path):
            raise HTTPException(status_code=404, detail=f"Modules path {modules_path} not found")
        
        # Search for the module file recursively
        found_path = None
        
        for root, dirs, files in os.walk(modules_path):
            if module_name in files:
                found_path = os.path.join(root, module_name)
                break
            
        if not found_path:
            raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
        
        # Read the module file
        try:
            with open(found_path, 'r') as f:
                import json
                module_content = json.load(f)
                
                # Get relative path from modules directory
                rel_path = os.path.relpath(found_path, modules_path)
                
                # Return module content along with metadata
                return {
                    "name": module_name,
                    "path": rel_path,
                    "full_path": found_path,
                    "content": module_content
                }
                
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Error parsing module file: {str(e)}"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error reading module file: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logging.error(f"Error accessing module: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    get_patients()
    uvicorn.run(app, host="0.0.0.0", port=8000)

