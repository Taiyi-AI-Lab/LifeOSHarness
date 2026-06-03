from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lifeostomanyagent.domain.models import WorldCreateRequest, WorldResponse
from lifeostomanyagent.server.auth import require_api_key
from lifeostomanyagent.server.deps import get_service
from lifeostomanyagent.server.services import LifeOSService

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.post("", response_model=WorldResponse)
def create_world(
    payload: WorldCreateRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> WorldResponse:
    try:
        return service.create_world(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("", response_model=list[WorldResponse])
def list_worlds(
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> list[WorldResponse]:
    return service.list_worlds()


@router.get("/{world_id}", response_model=WorldResponse)
def get_world(
    world_id: str,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> WorldResponse:
    try:
        return service.get_world(world_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
