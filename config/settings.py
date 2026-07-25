from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    github_token: str | None = None
    cors_origins: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
