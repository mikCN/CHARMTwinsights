import os
import requests
import json
import logging
import io
import base64
import numpy as np
import pandas as pd

# FastAPI imports
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# FHIR imports
from fhiry import Fhirsearch

# Matplotlib for visualization
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

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

from .config import settings

fs = Fhirsearch(fhir_base_url=settings.hapi_url)
SYNTHEA_SERVER_URL = settings.synthea_server_url


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
        
        # replace NaN values with None
        df = df.astype(object).where(pd.notna(df), None)
        
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
        
        # replace NaN values with None
        df = df.astype(object).where(pd.notna(df), None)
        
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
        
        # replace NaN values with None
        df = df.astype(object).where(pd.notna(df), None)
        
        conditions_dict = df.to_dict(orient='records')
        
        return {"conditions": conditions_dict, "count": len(conditions_dict)}
        
    except Exception as e:
        logger.error(f"Error retrieving conditions: {str(e)}", exc_info=True)
        raise HTTPException


# example queries:
# get specific a subset of properties from Patient resources in the default cohort
# {settings.hapi_url}/Patient?_tag=urn:charm:cohort|default&_elements=id,name,gender
# get all Patient resources in cohort named cohort1
# {settings.hapi_url}/Patient?_tag=urn:charm:cohort|cohort1
# same works for Conditions, Observations, etc.
# given a list of Patient IDs (from above), we can also get all Conditions for those patients
# {settings.hapi_url}/Condition?subject=Patient/123,Patient/456



# Import the FHIR utilities
from .fhir_utils import FHIRResourceProcessor

# Create a FHIR resource processor instance
fhir_processor = None

@app.on_event("startup")
async def startup_event():
    global fhir_processor
    fhir_processor = FHIRResourceProcessor(settings.hapi_url)

@app.get("/list-all-patient-conditions", response_class=JSONResponse)
async def list_all_patient_conditions():
    """
    Lists all conditions from all patients in the HAPI FHIR server.
    Returns a summary of conditions with their counts and associated patient details.
    """
    return await fhir_processor.process_fhir_resources('Condition', include_patients=True, include_patient_details=True)

@app.get("/list-all-patient-procedures", response_class=JSONResponse)
async def list_all_patient_procedures():
    """
    Lists all procedures from all patients in the HAPI FHIR server.
    Returns a summary of procedures with their counts and associated patient details.
    """
    return await fhir_processor.process_fhir_resources('Procedure', include_patients=True, include_patient_details=True)

@app.get("/list-all-patient-observations", response_class=JSONResponse)
async def list_all_patient_observations():
    """
    Lists all observations from all patients in the HAPI FHIR server.
    Returns a summary of observations with their counts and associated patient details.
    """
    return await fhir_processor.process_fhir_resources('Observation', include_patients=True, include_patient_details=True)

@app.get("/visualize-observations", response_class=Response)
async def visualize_observations(limit: int = Query(20, description="Limit the number of observation types to show")):
    """
    Generates a bar chart visualization of the most common observation types.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource('Observation', limit)


@app.get("/visualize-observations-by-gender", response_class=Response)
async def visualize_observations_by_gender(limit: int = Query(10, description="Limit the number of observation types to show per gender")):
    """
    Generates a bar chart visualization of the most common observation types broken down by gender.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource_by_gender('Observation', limit)


@app.get("/visualize-observations-by-age", response_class=Response)
async def visualize_observations_by_age(
    limit: int = Query(10, description="Limit the number of observation types to show per age bracket"),
    bracket_size: int = Query(5, description="Size of each age bracket in years")
):
    """
    Generates a bar chart visualization of the most common observation types broken down by age brackets.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource_by_age_bracket('Observation', limit, bracket_size)


@app.get("/visualize-conditions", response_class=Response)
async def visualize_conditions(limit: int = Query(20, description="Limit the number of condition types to show")):
    """
    Generates a bar chart visualization of the most common condition types.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource('Condition', limit)


@app.get("/visualize-conditions-by-gender", response_class=Response)
async def visualize_conditions_by_gender(limit: int = Query(10, description="Limit the number of condition types to show per gender")):
    """
    Generates a bar chart visualization of the most common condition types broken down by gender.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource_by_gender('Condition', limit)


@app.get("/visualize-conditions-by-age", response_class=Response)
async def visualize_conditions_by_age(
    limit: int = Query(10, description="Limit the number of condition types to show per age bracket"),
    bracket_size: int = Query(5, description="Size of each age bracket in years")
):
    """
    Generates a bar chart visualization of the most common condition types broken down by age brackets.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource_by_age_bracket('Condition', limit, bracket_size)


@app.get("/visualize-procedures", response_class=Response)
async def visualize_procedures(limit: int = Query(20, description="Limit the number of procedure types to show")):
    """
    Generates a bar chart visualization of the most common procedure types.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource('Procedure', limit)


@app.get("/visualize-procedures-by-gender", response_class=Response)
async def visualize_procedures_by_gender(limit: int = Query(10, description="Limit the number of procedure types to show per gender")):
    """
    Generates a bar chart visualization of the most common procedure types broken down by gender.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource_by_gender('Procedure', limit)


@app.get("/visualize-procedures-by-age", response_class=Response)
async def visualize_procedures_by_age(
    limit: int = Query(10, description="Limit the number of procedure types to show per age bracket"),
    bracket_size: int = Query(5, description="Size of each age bracket in years")
):
    """
    Generates a bar chart visualization of the most common procedure types broken down by age brackets.
    Returns a PNG image of the visualization.
    """
    return await fhir_processor.visualize_resource_by_age_bracket('Procedure', limit, bracket_size)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)