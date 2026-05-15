import logging

from backend.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("scoutflow").info("Starting ScoutFlow in %s mode", settings.app_env)
