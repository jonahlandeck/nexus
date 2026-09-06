from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .d1 import get_config
from .routers import grocery, intake, pantry, plan, profile

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("meatpotatoes")

app = FastAPI(title="Meat And Potatoes", version="0.1.0")

# The deployed SPA is served same-origin by the Worker; these origins only
# matter for local dev against the Vite server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(profile.router)
app.include_router(plan.router)
app.include_router(pantry.router)
app.include_router(grocery.router)


@app.get("/api/health")
def health(cfg: Settings = Depends(get_config)) -> dict:
    return {
        "ok": True,
        "provider": cfg.map_provider,
        "model": cfg.ollama_model,
    }
