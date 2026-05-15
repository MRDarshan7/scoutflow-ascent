import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()

if settings.gemini_api_key:
    print("Gemini enhancement enabled")
else:
    print("Gemini API key missing - fallback mode active")
