from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Any, Optional
import httpx
import logging

from ..config import settings  # expects settings.model_server_url

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modeling",
    tags=["Modeling"],
)

# --- Pydantic Models ---

class RegisterRequest(BaseModel):
    image: str = Field(..., example="irismodel:1.0.0")
    title: str
    short_description: str
    authors: str
    examples: Optional[List[Any]] = None
    readme: Optional[str] = None

class PredictRequest(BaseModel):
    image: str
    input: List[Any]

# --- Endpoints ---

@router.post("/models", response_class=JSONResponse)
async def register_model(req: RegisterRequest):
    """
    Register a new model with the model server.
    """
    url = f"{settings.model_server_url}/models"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=req.dict())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Model server error: {e.response.text}")
        detail = e.response.text or "Error registering model"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error registering model: {e}")
        raise HTTPException(status_code=500, detail="Model server unreachable")

@router.post("/predict", response_class=JSONResponse)
async def predict(request: PredictRequest):
    """
    Make a prediction using a registered model.
    """
    url = f"{settings.model_server_url}/predict"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=request.dict())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Model server error: {e.response.text}")
        detail = e.response.text or "Error making prediction"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail="Model server unreachable")

@router.get("/models", response_class=JSONResponse)
async def list_models():
    """
    List all registered models with core metadata.
    """
    url = f"{settings.model_server_url}/models"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Model server error: {e.response.text}")
        detail = e.response.text or "Error listing models"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Model server unreachable")

@router.get("/models/{image_tag}", response_class=JSONResponse)
async def model_info(image_tag: str):
    """
    Get detailed information about a specific model.
    """
    url = f"{settings.model_server_url}/models/{image_tag}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Model server error: {e.response.text}")
        detail = e.response.text or f"Error fetching model info for {image_tag}"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Error fetching model info for {image_tag}: {e}")
        raise HTTPException(status_code=500, detail="Model server unreachable")
