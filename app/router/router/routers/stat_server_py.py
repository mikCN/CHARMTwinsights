from fastapi import APIRouter, HTTPException, Query, Path, Request
from fastapi.responses import JSONResponse
import httpx
import logging

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stats",
    tags=["Patient Statistics"],
)

BACKEND_URL = settings.stat_server_py_url.rstrip("/")

@router.get("/patients", response_class=JSONResponse)
async def proxy_get_patients(
    request: Request,
    name: str = Query(None, description="Patient name to search for"),
    gender: str = Query(None, description="Patient gender"),
    birthdate: str = Query(None, description="Patient birthdate (YYYY-MM-DD)"),
    _count: int = Query(10, description="Number of results to return")
):
    # Forward query parameters to backend
    params = request.query_params
    url = f"{BACKEND_URL}/patients"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error fetching patients"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")

@router.get("/patients/{patient_id}", response_class=JSONResponse)
async def proxy_get_patient_by_id(
    patient_id: str = Path(..., description="Patient FHIR resource ID")
):
    url = f"{BACKEND_URL}/patients/{patient_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or f"Error fetching patient {patient_id}"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")

@router.get("/conditions", response_class=JSONResponse)
async def proxy_get_conditions(
    request: Request,
    patient: str = Query(None, description="Patient reference (Patient/id)"),
    code: str = Query(None, description="Condition code (system|code format)")
):
    params = request.query_params
    url = f"{BACKEND_URL}/conditions"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error fetching conditions"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")
