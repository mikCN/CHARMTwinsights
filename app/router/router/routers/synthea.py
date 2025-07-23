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
    num_patients: int = Query(10, ge=1, le=100),
    num_years: int = Query(1, ge=1, le=100),
    cohort_id: str = Query("default", min_length=1)
):
    url = f"{settings.synthea_server_url}/synthetic-patients"
    data = {
        "num_patients": num_patients,
        "num_years": num_years,
        "cohort_id": cohort_id,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()
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


@router.get("/patients-and-cohorts", response_class=JSONResponse)
async def get_patients_and_cohorts():
    """
    Get a list of all patients and their associated cohorts from the HAPI FHIR server.
    """
    url = f"{settings.synthea_server_url}/patients-and-cohorts"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Synthea error (patients-and-cohorts): {e.response.text}")
        detail = e.response.text or "Error fetching patients and cohorts"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error fetching patients and cohorts: {e}")
        raise HTTPException(status_code=500, detail="Synthea server unreachable")
