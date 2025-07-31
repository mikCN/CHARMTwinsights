from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import logging

from ..config import settings  # expects settings.synthea_server_url

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/synthetic/synthea",
    tags=["Synthetic Data Generation"],
)

@router.post("/generate-synthetic-patients", response_class=JSONResponse)
async def get_synthetic_patients(
    num_patients: int = Query(10, ge=1, le=5000),
    num_years: int = Query(1, ge=1, le=100),
    cohort_id: str = Query(None)
):
    # Validate cohort_id if provided by the user
    if cohort_id and '_' in cohort_id:
        raise HTTPException(
            status_code=400, 
            detail="Cohort ID cannot contain underscores. Please use alphanumeric characters and hyphens instead."
        )
    # If no cohort_id is provided, generate one based on existing cohorts
    if cohort_id is None:
        try:
            # Get the list of existing cohorts
            cohorts_url = f"{settings.synthea_server_url}/list-all-cohorts"
            async with httpx.AsyncClient(timeout=30.0) as client:
                cohorts_resp = await client.get(cohorts_url)
                cohorts_resp.raise_for_status()
                cohorts_data = cohorts_resp.json()
                total_cohorts = cohorts_data.get("total_cohorts", 0)
                # Use 'cohort' prefix with a number, avoiding underscores which can cause issues with FHIR IDs
                cohort_id = f"cohort{total_cohorts + 1}"
                logger.info(f"Auto-generated cohort ID: {cohort_id}")
        except Exception as e:
            logger.error(f"Error fetching cohorts for auto-ID generation: {e}")
            # Fallback to a timestamp-based ID if we can't get the cohort count
            import time
            # Avoid underscores in the cohort ID as they can cause issues with FHIR IDs
            cohort_id = f"cohort{int(time.time())}"
            logger.info(f"Fallback cohort ID: {cohort_id}")
    
    url = f"{settings.synthea_server_url}/synthetic-patients"
    data = {
        "num_patients": num_patients,
        "num_years": num_years,
        "cohort_id": cohort_id,
    }
    try:
        # Dynamic timeout based on patient count and years
        # Base timeout: 30s minimum
        # Add 0.5s per patient per year, capped at 1800s (30 minutes)
        base_timeout = 30.0
        per_patient_per_year = 0.5  # 0.5 seconds per patient per year
        calculated_timeout = base_timeout + (num_patients * num_years * per_patient_per_year)
        timeout = min(1800.0, calculated_timeout)
        
        logger.info(f"Generating {num_patients} patients with timeout of {timeout:.1f} seconds")
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=data)
            resp.raise_for_status()
            
            # Get the response data
            response_data = resp.json()
            
            # Add the cohort_id to the response if it was auto-generated
            if cohort_id and "cohort_id" not in response_data:
                response_data["cohort_id"] = cohort_id
                logger.info(f"Adding auto-generated cohort ID {cohort_id} to response")
                
            return response_data
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea backend error: {e.response.text}")
        detail = e.response.text or "Error generating synthetic patients"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting Synthea backend: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable")

@router.get("/modules", response_class=JSONResponse)
async def get_synthea_modules_list():
    """
    Get the list of available Synthea modules.
    """
    url = f"{settings.synthea_server_url}/modules"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea error: {e.response.text}")
        detail = e.response.text or "Error fetching Synthea modules"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error fetching Synthea modules: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable")

@router.get("/modules/{module_name}", response_class=JSONResponse)
async def get_module_content(module_name: str):
    """
    Get the content of a specific Synthea module.
    """
    url = f"{settings.synthea_server_url}/modules/{module_name}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea error ({module_name}): {e.response.text}")
        detail = e.response.text or f"Error fetching Synthea module {module_name}"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error fetching Synthea module {module_name}: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable")


@router.get("/list-all-patients", response_class=JSONResponse)
async def list_all_patients():
    """
    Get a list of all patients with their cohort IDs, date of birth, and display/text fields from the HAPI FHIR server.
    """
    url = f"{settings.synthea_server_url}/list-all-patients"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea error (list-all-patients): {e.response.text}")
        detail = e.response.text or "Error fetching patients list"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error fetching patients list: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable")


@router.get("/list-all-cohorts", response_class=JSONResponse)
async def list_all_cohorts():
    """
    Get a list of all cohorts with their patient counts and sources from the HAPI FHIR server.
    """
    url = f"{settings.synthea_server_url}/list-all-cohorts"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea error (list-all-cohorts): {e.response.text}")
        detail = e.response.text or "Error fetching cohorts list"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error fetching cohorts list: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable")


@router.get("/count-patient-keys", response_class=JSONResponse)
async def count_patient_keys(cohort_id: str = None):
    """
    Get counts of leaf keys in patient JSON data for a specific cohort or all patients.
    
    This endpoint analyzes the structure of patient data and counts how many times each
    leaf key (keys whose values are not dictionaries or lists) appears across patients.
    
    Args:
        cohort_id: Optional ID of the cohort to analyze. If not provided, all patients are analyzed.
    """
    url = f"{settings.synthea_server_url}/count-patient-keys"
    if cohort_id:
        url += f"?cohort_id={cohort_id}"
    
    try:
        # This operation might take a while for large patient sets
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea error (count-patient-keys): {e.response.text}")
        detail = e.response.text or "Error analyzing patient keys"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error analyzing patient keys: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable or operation timed out")
