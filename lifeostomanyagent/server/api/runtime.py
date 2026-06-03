from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lifeostomanyagent.domain.models import (
    ContextRequest,
    ContextResponse,
    DreamLatestResponse,
    DreamRunRequest,
    DreamRunResponse,
    SessionEventRequest,
)
from lifeostomanyagent.server.auth import require_api_key
from lifeostomanyagent.server.deps import get_service
from lifeostomanyagent.server.services import LifeOSService

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.post("/context", response_model=ContextResponse)
def build_context(
    payload: ContextRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> ContextResponse:
    try:
        return service.build_context(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/session/start")
def session_start(
    payload: SessionEventRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> dict:
    try:
        return service.session_start(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/session/end")
def session_end(
    payload: SessionEventRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> dict:
    try:
        return service.session_end(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/turn/begin")
def turn_begin(
    payload: SessionEventRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> dict:
    try:
        return service.turn_begin(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/turn/finish")
def turn_finish(
    payload: SessionEventRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> dict:
    try:
        return service.turn_finish(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/dreams/run", response_model=DreamRunResponse)
def dream_run(
    payload: DreamRunRequest,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> DreamRunResponse:
    try:
        return service.dream_run(payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/dreams/latest", response_model=DreamLatestResponse)
def dream_latest(
    world_id: str,
    _: str = Depends(require_api_key),
    service: LifeOSService = Depends(get_service),
) -> DreamLatestResponse:
    try:
        return service.dream_latest(world_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
