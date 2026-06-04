from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lifeostomanyagent.domain.models import (
    PackCreateRequest,
    PackResponse,
)
from lifeostomanyagent.server.auth import require_api_key
from lifeostomanyagent.server.deps import get_service
from lifeostomanyagent.server.services import LifeOSService

router = APIRouter(prefix="/packs", tags=["packs"])


@router.post("/presets/alice", response_model=PackResponse)
def install_alice_preset(
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> PackResponse:
    return service.ensure_alice_preset()


@router.post("", response_model=PackResponse)
def create_pack(
    payload: PackCreateRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> PackResponse:
    try:
        return service.create_pack(payload)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[PackResponse])
def list_packs(
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> list[PackResponse]:
    return service.list_packs()


@router.get("/{pack_id}", response_model=PackResponse)
def get_pack(
    pack_id: str,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> PackResponse:
    try:
        return service.get_pack(pack_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
