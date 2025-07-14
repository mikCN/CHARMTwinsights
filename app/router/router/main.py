from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import routers
from .routers import synthea
from .routers import modeling
from .routers import stat_server_py

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

app = FastAPI(
    title="CHARMTwinsight API Gateway",
    description="Frontend REST API for CHARMTwinsight microservices.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for all origins for development; restrict for prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to your frontend domains in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(synthea.router)
app.include_router(modeling.router)
app.include_router(stat_server_py.router)

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
