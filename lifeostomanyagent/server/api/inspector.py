from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from lifeostomanyagent.server.auth import require_api_key
from lifeostomanyagent.server.deps import get_service
from lifeostomanyagent.server.services import LifeOSService

router = APIRouter(prefix="/inspector", tags=["inspector"])


@router.get("/worlds/{world_id}/state")
def get_world_state(
    world_id: str,
    limit: int = 100,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return service.inspect_world_state(world_id, limit=limit)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
