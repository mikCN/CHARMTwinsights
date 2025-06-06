import os
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from fhiry.fhirsearch import Fhirsearch
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FHIR API Server",
    description="A REST API for accessing FHIR resources from HAPI FHIR server",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fs = Fhirsearch(fhir_base_url="http://hapi:8080/fhir")
SYNTHEA_SERVER_URL = "http://synthea_server:8000"

@app.get("/")
def read_root():
    return {"message": "Hello from the mlflow-server!!!", "status": "active"}


@app.get("/synthea/modules", response_class=JSONResponse)
async def get_synthea_modules_list():
    try:
        # Access the shared volume path directly
        modules_path = "/synthea/modules"
        
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
    
    

@app.get("/synthea/module/{module_name}", response_class=JSONResponse)
async def get_module_content(module_name: str):
    try:
        # Ensure module_name has .json extension
        if not module_name.endswith('.json'):
            module_name += '.json'
            
        # Access the shared volume path directly
        modules_path = "/synthea/modules"
        
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
    


@app.get("/health", response_class=JSONResponse)
async def health_check():
    return {"status": "healthy"}

@app.get("/patients", response_class=JSONResponse)
async def get_patients(
    name: str = Query(None, description="Patient name to search for"),
    gender: str = Query(None, description="Patient gender"),
    birthdate: str = Query(None, description="Patient birthdate (YYYY-MM-DD)"),
    _count: int = Query(10, description="Number of results to return")
):
    try:
        search_params = {}
        if name:
            search_params["name"] = name
        if gender:
            search_params["gender"] = gender
        if birthdate:
            search_params["birthdate"] = birthdate
        if _count:
            search_params["_count"] = str(_count)
            
        logger.info(f"Searching for patients with params: {search_params}")
        
        df = fs.search(resource_type="Patient", search_parameters=search_params)
        
        if df is not None and not df.empty:
            logger.info(f"Found {len(df)} patients")
            logger.info(f"DataFrame columns: {df.columns.tolist()}")
        else:
            logger.warning("No patients found or empty dataframe returned")
            return {"patients": []}
        
        df = df.where(pd.notna(df), None)
        
        patients_dict = df.to_dict(orient='records')
        
        return {"patients": patients_dict, "count": len(patients_dict)}
        
    except Exception as e:
        logger.error(f"Error retrieving patients: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving patients: {str(e)}")

@app.get("/patients/{patient_id}", response_class=JSONResponse)
async def get_patient_by_id(patient_id: str):
    try:
        search_params = {"_id": patient_id}
        df = fs.search(resource_type="Patient", search_parameters=search_params)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"Patient with ID {patient_id} not found")
        
        df = df.where(pd.notna(df), None)
        
        patient_dict = df.to_dict(orient='records')[0]
        
        return patient_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving patient {patient_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving patient: {str(e)}")

@app.get("/conditions", response_class=JSONResponse)
async def get_conditions(
    patient: str = Query(None, description="Patient reference (Patient/id)"),
    code: str = Query(None, description="Condition code (system|code format)")
):
    try:
        search_params = {}
        if patient:
            search_params["subject"] = f"Patient/{patient}"
        if code:
            search_params["code"] = code
            
        df = fs.search(resource_type="Condition", search_parameters=search_params)
        
        if df is None or df.empty:
            return {"conditions": []}
        
        df = df.where(pd.notna(df), None)
        
        conditions_dict = df.to_dict(orient='records')
        
        return {"conditions": conditions_dict, "count": len(conditions_dict)}
        
    except Exception as e:
        logger.error(f"Error retrieving conditions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving conditions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)