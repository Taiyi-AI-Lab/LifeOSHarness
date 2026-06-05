from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from lifeostomanyagent.domain.models import (
    ContextRequest,
    ContextResponse,
    WorldCreateRequest,
    WorldResponse,
)


@dataclass
class ClientConfig:
    server_url: str = "http://127.0.0.1:8000"
    api_key: str = "dev-lifeos-key-change-me"
    default_world_id: str | None = None


class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path.home() / ".lifeos" / "config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> ClientConfig:
        if not self.path.exists():
            return ClientConfig()
        data = json.loads(self.path.read_text("utf-8"))
        return ClientConfig(**data)

    def save(self, config: ClientConfig) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "server_url": config.server_url,
                    "api_key": config.api_key,
                    "default_world_id": config.default_world_id,
                },
                ensure_ascii=False,
                indent=2,
            ),
            "utf-8",
        )


class LifeOSClient:
    def __init__(self, config: ClientConfig):
        self.config = config
        self._client = httpx.Client(
            base_url=config.server_url.rstrip("/"),
            headers={"X-API-Key": config.api_key},
            timeout=60.0,
            trust_env=False,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LifeOSClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict:
        response = self._client.get("/health")
        response.raise_for_status()
        return response.json()

    def install_chenyuan_preset(self) -> dict:
        response = self._client.post("/packs/presets/chenyuan")
        response.raise_for_status()
        return response.json()

    def create_world(self, pack_id: str, display_name: str) -> WorldResponse:
        payload = WorldCreateRequest(pack_id=pack_id, display_name=display_name)
        response = self._client.post("/worlds", json=payload.model_dump())
        response.raise_for_status()
        return WorldResponse.model_validate(response.json())

    def list_worlds(self) -> list[WorldResponse]:
        response = self._client.get("/worlds")
        response.raise_for_status()
        return [WorldResponse.model_validate(item) for item in response.json()]

    def pull_context(
        self,
        *,
        world_id: str,
        message: str,
        connector_id: str = "generic",
        session_id: str | None = None,
    ) -> ContextResponse:
        payload = ContextRequest(
            world_id=world_id,
            user_message=message,
            connector_id=connector_id,
            session_id=session_id,
        )
        response = self._client.post("/runtime/context", json=payload.model_dump())
        response.raise_for_status()
        return ContextResponse.model_validate(response.json())

    def session_start(self, *, world_id: str, connector_id: str, session_id: str) -> dict:
        response = self._client.post(
            "/runtime/session/start",
            json={
                "world_id": world_id,
                "connector_id": connector_id,
                "session_id": session_id,
            },
        )
        response.raise_for_status()
        return response.json()

    def session_end(
        self,
        *,
        world_id: str,
        connector_id: str,
        session_id: str,
        meaningful: bool = True,
    ) -> dict:
        response = self._client.post(
            "/runtime/session/end",
            json={
                "world_id": world_id,
                "connector_id": connector_id,
                "session_id": session_id,
                "meaningful": meaningful,
            },
        )
        response.raise_for_status()
        return response.json()

    def dream_run(
        self,
        *,
        world_id: str,
        dream_date: str | None = None,
        force: bool = False,
    ) -> dict:
        response = self._client.post(
            "/runtime/dreams/run",
            json={
                "world_id": world_id,
                "dream_date": dream_date,
                "force": force,
            },
        )
        response.raise_for_status()
        return response.json()

    def dream_latest(self, *, world_id: str) -> dict:
        response = self._client.get("/runtime/dreams/latest", params={"world_id": world_id})
        response.raise_for_status()
        return response.json()
