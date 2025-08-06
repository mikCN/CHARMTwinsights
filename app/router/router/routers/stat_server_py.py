from fastapi import APIRouter, HTTPException, Query, Path, Request, Response
from fastapi.responses import JSONResponse
import httpx
import logging
from typing import List, Optional

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stats",
    tags=["Patient Statistics"],
)

BACKEND_URL = settings.stat_server_py_url.rstrip("/")
HAPI_URL = settings.hapi_server_url.rstrip("/")

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

@router.get("/patients/{patient_id}/$everything")
async def patient_everything(
    patient_id: str = Path(..., description="The FHIR Patient resource ID."),
    start: Optional[str] = Query(
        None,
        description=(
            "Care date start (inclusive). Format: YYYY, YYYY-MM, YYYY-MM-DD, or YYYY-MM-DDThh:mm:ss+zz:zz"
        ),
        example="2018-01-01"
    ),
    end: Optional[str] = Query(
        None,
        description=(
            "Care date end (inclusive). Format: YYYY, YYYY-MM, YYYY-MM-DD, or YYYY-MM-DDThh:mm:ss+zz:zz"
        ),
        example="2020-12-31"
    ),
    _since: Optional[str] = Query(
        None,
        description="Return resources updated after this instant. Format: YYYY-MM-DDThh:mm:ss+zz:zz or similar.",
        example="2022-01-01T00:00:00Z"
    ),
    _type: Optional[List[str]] = Query(
        None,
        description="Comma-delimited FHIR resource types to include. Example: Observation,Condition",
        example=["Observation", "Condition"]
    ),
    _count: Optional[int] = Query(
        None,
        description="Page size for results (see HAPI docs)."
    ),
):
    """Wraps the hapi:/fhir/Patient/{id}/$everything endpoint to fetch all resources related to a patient. See https://hl7.org/fhir/operation-patient-everything.html"""
    # Construct query params for the backend
    query_params = {}
    if start:
        query_params['start'] = start
    if end:
        query_params['end'] = end
    if _since:
        query_params['_since'] = _since
    if _type:
        # FHIR allows comma-separated or multiple _type params
        # We'll join as comma-separated for simplicity
        query_params['_type'] = ",".join(_type)
    if _count is not None:
        query_params['_count'] = str(_count)

    backend_url = f"{HAPI_URL}/Patient/{patient_id}/$everything"

    # Forward the request to HAPI
    async with httpx.AsyncClient() as client:
        resp = await client.get(backend_url, params=query_params)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/fhir+json"),
        )

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
async def proxy_visualize_observations(
    limit: int = Query(20, description="Limit the number of observation types to show"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common observation types.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of observation types to show
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-observations"
    params = {"limit": limit}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
async def proxy_visualize_observations_by_gender(
    limit: int = Query(10, description="Limit the number of observation types to show per gender"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common observation types broken down by gender.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of observation types to show per gender
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-observations-by-gender"
    params = {"limit": limit}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
    bracket_size: int = Query(5, description="Size of each age bracket in years"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common observation types broken down by age brackets.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of observation types to show per age bracket
    - bracket_size: Size of each age bracket in years
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-observations-by-age"
    params = {"limit": limit, "bracket_size": bracket_size}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
async def proxy_visualize_conditions(
    limit: int = Query(20, description="Limit the number of condition types to show"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common condition types.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of condition types to show
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-conditions"
    params = {"limit": limit}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
async def proxy_visualize_conditions_by_gender(
    limit: int = Query(10, description="Limit the number of condition types to show per gender"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common condition types broken down by gender.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of condition types to show per gender
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-conditions-by-gender"
    params = {"limit": limit}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
    bracket_size: int = Query(5, description="Size of each age bracket in years"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common condition types broken down by age brackets.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of condition types to show per age bracket
    - bracket_size: Size of each age bracket in years
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-conditions-by-age"
    params = {"limit": limit, "bracket_size": bracket_size}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
async def proxy_visualize_procedures(
    limit: int = Query(20, description="Limit the number of procedure types to show"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common procedure types.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of procedure types to show
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-procedures"
    params = {"limit": limit}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
async def proxy_visualize_procedures_by_gender(
    limit: int = Query(10, description="Limit the number of procedure types to show per gender"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common procedure types broken down by gender.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of procedure types to show per gender
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-procedures-by-gender"
    params = {"limit": limit}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
    bracket_size: int = Query(5, description="Size of each age bracket in years"),
    cohort_id: str = Query(None, description="Optional cohort ID to filter resources by cohort tag")
):
    """
    Generates a bar chart visualization of the most common procedure types broken down by age brackets.
    Returns a PNG image of the visualization.
    
    Parameters:
    - limit: Maximum number of procedure types to show per age bracket
    - bracket_size: Size of each age bracket in years
    - cohort_id: Optional cohort ID to filter resources by cohort tag
    """
    url = f"{BACKEND_URL}/visualize-procedures-by-age"
    params = {"limit": limit, "bracket_size": bracket_size}
    if cohort_id:
        params["cohort_id"] = cohort_id
    
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
