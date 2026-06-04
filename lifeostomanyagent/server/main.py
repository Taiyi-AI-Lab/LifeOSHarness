from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from lifeostomanyagent.config import settings
from lifeostomanyagent.server.api.packs import router as packs_router
from lifeostomanyagent.server.api.runtime import router as runtime_router
from lifeostomanyagent.server.api.worlds import router as worlds_router
from lifeostomanyagent.server.db.models import get_db, init_db
from lifeostomanyagent.server.services import LifeOSService


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.lifeos_data_root.mkdir(parents=True, exist_ok=True)
    settings.worlds_data_root.mkdir(parents=True, exist_ok=True)
    init_db()
    db = get_db()
    try:
        LifeOSService(db).ensure_alice_preset()
    finally:
        db.close()
    yield


app = FastAPI(title="LifeOS Platform", version="0.1.0", lifespan=lifespan)
app.include_router(packs_router)
app.include_router(worlds_router)
app.include_router(runtime_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
