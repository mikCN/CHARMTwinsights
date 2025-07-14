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

from .config import settings

fs = Fhirsearch(fhir_base_url=settings.hapi_url)
SYNTHEA_SERVER_URL = settings.synthea_server_url

@app.get("/")
def read_root():
    return {"message": "Hello from the pyserver!!!", "status": "active"}


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