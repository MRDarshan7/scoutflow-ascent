import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    monitor_interval_minutes: int = _int_env("MONITOR_INTERVAL_MINUTES", 360)


settings = Settings()

if settings.gemini_api_key:
    print("Gemini enhancement enabled")
else:
    print("Gemini API key missing - fallback mode active")
