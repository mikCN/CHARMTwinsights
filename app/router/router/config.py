import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    synthea_server_url: str = os.getenv("SYNTHEA_SERVER_URL", "http://synthea_server:8000")
    model_server_url: str = os.getenv("MODEL_SERVER_URL", "http://model_server:8000")
    # add other settings as needed

settings = Settings()
