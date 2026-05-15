from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import check_connection, init_db
from backend.logging_config import configure_logging


configure_logging()

app = FastAPI(title="ScoutFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "ScoutFlow", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    check_connection()
    return {"status": "ok", "database": "connected"}
