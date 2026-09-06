from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import grocery, intake, pantry, plan, profile

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("meatpotatoes")

settings = get_settings()
app = FastAPI(title="Meat And Potatoes", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin, "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(profile.router)
app.include_router(plan.router)
app.include_router(pantry.router)
app.include_router(grocery.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    log.info("provider=%s ollama=%s model=%s", settings.map_provider, settings.ollama_url, settings.ollama_model)
    if settings.map_provider == "scraperapi" and not settings.scraperapi_key:
        log.warning("MAP_PROVIDER=scraperapi but SCRAPERAPI_KEY is empty - grocery matching will error until you set it in .env")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "provider": settings.map_provider,
        "model": settings.ollama_model,
    }
