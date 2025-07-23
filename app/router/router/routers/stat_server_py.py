from fastapi import APIRouter, HTTPException, Query, Path, Request, Response
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


@router.get("/all-patient-conditions", response_class=JSONResponse)
async def proxy_list_all_patient_conditions():
    """
    Lists all conditions from all patients in the HAPI FHIR server.
    Returns a summary of conditions with their counts and details.
    """
    url = f"{BACKEND_URL}/list-all-patient-conditions"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout since this might be a larger query
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error fetching all patient conditions"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/all-patient-procedures", response_class=JSONResponse)
async def proxy_list_all_patient_procedures():
    """
    Lists all procedures from all patients in the HAPI FHIR server.
    Returns a summary of procedures with their counts and associated patient IDs.
    """
    url = f"{BACKEND_URL}/list-all-patient-procedures"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout since this might be a larger query
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error fetching all patient procedures"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/all-patient-observations", response_class=JSONResponse)
async def proxy_list_all_patient_observations():
    """
    Lists all observations from all patients in the HAPI FHIR server.
    Returns a summary of observations with their counts and associated patient IDs.
    """
    url = f"{BACKEND_URL}/list-all-patient-observations"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout since this might be a larger query
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error fetching all patient observations"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-observations", response_class=Response)
async def proxy_visualize_observations(limit: int = Query(20, description="Limit the number of observation types to show")):
    """
    Generates a bar chart visualization of the most common observation types.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-observations"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating observation visualization"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-observations-by-gender", response_class=Response)
async def proxy_visualize_observations_by_gender(limit: int = Query(10, description="Limit the number of observation types to show per gender")):
    """
    Generates a bar chart visualization of the most common observation types broken down by gender.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-observations-by-gender"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating observation visualization by gender"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-observations-by-age", response_class=Response)
async def proxy_visualize_observations_by_age(
    limit: int = Query(10, description="Limit the number of observation types to show per age bracket"),
    bracket_size: int = Query(5, description="Size of each age bracket in years")
):
    """
    Generates a bar chart visualization of the most common observation types broken down by age brackets.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-observations-by-age"
    params = {"limit": limit, "bracket_size": bracket_size}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating observation visualization by age"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-conditions", response_class=Response)
async def proxy_visualize_conditions(limit: int = Query(20, description="Limit the number of condition types to show")):
    """
    Generates a bar chart visualization of the most common condition types.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-conditions"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating condition visualization"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-conditions-by-gender", response_class=Response)
async def proxy_visualize_conditions_by_gender(limit: int = Query(10, description="Limit the number of condition types to show per gender")):
    """
    Generates a bar chart visualization of the most common condition types broken down by gender.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-conditions-by-gender"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating condition visualization by gender"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-conditions-by-age", response_class=Response)
async def proxy_visualize_conditions_by_age(
    limit: int = Query(10, description="Limit the number of condition types to show per age bracket"),
    bracket_size: int = Query(5, description="Size of each age bracket in years")
):
    """
    Generates a bar chart visualization of the most common condition types broken down by age brackets.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-conditions-by-age"
    params = {"limit": limit, "bracket_size": bracket_size}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating condition visualization by age"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-procedures", response_class=Response)
async def proxy_visualize_procedures(limit: int = Query(20, description="Limit the number of procedure types to show")):
    """
    Generates a bar chart visualization of the most common procedure types.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-procedures"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating procedure visualization"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-procedures-by-gender", response_class=Response)
async def proxy_visualize_procedures_by_gender(limit: int = Query(10, description="Limit the number of procedure types to show per gender")):
    """
    Generates a bar chart visualization of the most common procedure types broken down by gender.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-procedures-by-gender"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating procedure visualization by gender"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")


@router.get("/visualize-procedures-by-age", response_class=Response)
async def proxy_visualize_procedures_by_age(
    limit: int = Query(10, description="Limit the number of procedure types to show per age bracket"),
    bracket_size: int = Query(5, description="Size of each age bracket in years")
):
    """
    Generates a bar chart visualization of the most common procedure types broken down by age brackets.
    Returns a PNG image of the visualization.
    """
    url = f"{BACKEND_URL}/visualize-procedures-by-age"
    params = {"limit": limit, "bracket_size": bracket_size}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image generation
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return Response(content=resp.content, media_type="image/png")
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend error: {e.response.text}")
        detail = e.response.text or "Error generating procedure visualization by age"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error contacting backend: {e}")
        raise HTTPException(status_code=500, detail="stat_server_py unreachable")
