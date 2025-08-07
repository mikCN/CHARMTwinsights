from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    hapi_url: str = "http://hapi:8080/fhir"
    synthea_server_url: str = "http://synthea_server:8000"

    class Config:
        env_file = ".env"

settings = Settings()
