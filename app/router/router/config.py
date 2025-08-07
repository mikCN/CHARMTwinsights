import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    synthea_server_url: str = os.getenv("SYNTHEA_SERVER_URL", "http://synthea_server:8000")
    model_server_url: str = os.getenv("MODEL_SERVER_URL", "http://model_server:8000")
    stat_server_py_url: str = os.getenv("STAT_SERVER_PY_URL", "http://stat_server_py:8000")
    hapi_server_url: str = os.getenv("HAPI_SERVER_URL", "http://hapi:8080/fhir")
    # add other settings as needed

settings = Settings()
