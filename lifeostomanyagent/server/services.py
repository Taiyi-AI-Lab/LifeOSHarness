from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import redis
from sqlalchemy.orm import Session

from lifeostomanyagent.config import settings
from lifeostomanyagent.domain.models import (
    AgentIdentity,
    AgentPackConfig,
    BehaviorProfile,
    BehaviorTrajectory,
    ContextRequest,
    ContextResponse,
    DreamLatestResponse,
    DreamRunRequest,
    DreamRunResponse,
    PackCreateRequest,
    PackResponse,
    RuntimeModules,
    SessionEventRequest,
    WorldCreateRequest,
    WorldOverrides,
    WorldResponse,
    WorldRules,
)
from lifeostomanyagent.server.db.models import AgentPackRow, SessionRecordRow, WorldInstanceRow
from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine
from lifeostomanyagent.server.presets.alice import build_alice_pack_config


class LifeOSService:
    def __init__(self, db: Session):
        self.db = db
        self._redis: redis.Redis | None = None
        if settings.redis_url:
            try:
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
            except redis.RedisError:
                self._redis = None

    def ensure_alice_preset(self) -> PackResponse:
        config_json = build_alice_pack_config()
        existing = self.db.query(AgentPackRow).filter(AgentPackRow.pack_id == "alice").one_or_none()
        if existing:
            existing.config_json = config_json
            existing.display_name = "Alice"
            self.db.commit()
            self.db.refresh(existing)
            return self._pack_response(existing)
        row = AgentPackRow(
            id=str(uuid.uuid4()),
            pack_id="alice",
            display_name="Alice",
            config_json=config_json,
            is_preset=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._pack_response(row)

    def create_pack(self, payload: PackCreateRequest) -> PackResponse:
        if self.db.query(AgentPackRow).filter(AgentPackRow.pack_id == payload.pack_id).one_or_none():
            raise ValueError(f"pack already exists: {payload.pack_id}")
        config = AgentPackConfig(
            pack_id=payload.pack_id,
            display_name=payload.display_name,
            identity=payload.identity,
            behavior_profile=payload.behavior_profile or BehaviorProfile(),
            behavior_trajectory=payload.behavior_trajectory or BehaviorTrajectory(),
            world_rules=payload.world_rules or WorldRules(),
            runtime_modules=payload.runtime_modules or RuntimeModules(),
            base_system_prompt=payload.base_system_prompt,
            is_preset=False,
        )
        row = AgentPackRow(
            id=str(uuid.uuid4()),
            pack_id=payload.pack_id,
            display_name=payload.display_name,
            config_json=config.model_dump(),
            is_preset=False,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._pack_response(row)

    def get_pack(self, pack_id: str) -> PackResponse:
        row = self._get_pack_row(pack_id)
        return self._pack_response(row)

    def list_packs(self) -> list[PackResponse]:
        rows = self.db.query(AgentPackRow).order_by(AgentPackRow.created_at.asc()).all()
        return [self._pack_response(row) for row in rows]

    def create_world(self, payload: WorldCreateRequest) -> WorldResponse:
        self._get_pack_row(payload.pack_id)
        world_id = str(uuid.uuid4())
        runtime_dir = settings.worlds_data_root / world_id
        runtime_dir.mkdir(parents=True, exist_ok=True)
        overrides = payload.overrides or WorldOverrides()
        row = WorldInstanceRow(
            id=str(uuid.uuid4()),
            world_id=world_id,
            pack_id=payload.pack_id,
            display_name=payload.display_name,
            overrides_json=overrides.model_dump(),
            runtime_dir=str(runtime_dir),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._world_response(row)

    def get_world(self, world_id: str) -> WorldResponse:
        row = self._get_world_row(world_id)
        return self._world_response(row)

    def list_worlds(self) -> list[WorldResponse]:
        rows = self.db.query(WorldInstanceRow).order_by(WorldInstanceRow.created_at.asc()).all()
        return [self._world_response(row) for row in rows]

    def build_context(self, payload: ContextRequest) -> ContextResponse:
        engine = self._engine_for_world(payload.world_id)
        use_cache = not bool(engine.dreams)
        cache_key = self._cache_key(payload)
        cached = self._cache_get(cache_key) if use_cache else None
        if cached:
            return ContextResponse.model_validate(cached)

        result = engine.build_context(
            payload.user_message,
            connector_id=payload.connector_id,
            extra_blocks=payload.extra_blocks or None,
        )
        response = ContextResponse(
            world_id=payload.world_id,
            connector_id=result["connector_id"],
            system=result["system"],
            order=result["order"],
            blocks=[
                {"id": block["id"], "tag": block.get("tag"), "content_length": block["contentLength"]}
                for block in result["blocks"]
            ],
        )
        if use_cache:
            self._cache_set(cache_key, response.model_dump())
        return response

    def session_start(self, payload: SessionEventRequest) -> dict:
        from datetime import datetime, timezone

        engine = self._engine_for_world(payload.world_id)
        state = engine.on_chat_started(connector_id=payload.connector_id, session_id=payload.session_id)
        row = SessionRecordRow(
            world_id=payload.world_id,
            connector_id=payload.connector_id,
            session_id=payload.session_id,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.commit()
        self._invalidate_world_cache(payload.world_id)
        return {"ok": True, "emotion": state}

    def session_end(self, payload: SessionEventRequest) -> dict:
        from datetime import datetime, timezone

        engine = self._engine_for_world(payload.world_id)
        state = engine.on_chat_ended(
            connector_id=payload.connector_id,
            session_id=payload.session_id,
            meaningful=payload.meaningful,
        )
        record = (
            self.db.query(SessionRecordRow)
            .filter(
                SessionRecordRow.world_id == payload.world_id,
                SessionRecordRow.session_id == payload.session_id,
            )
            .order_by(SessionRecordRow.started_at.desc())
            .first()
        )
        if record and record.ended_at is None:
            record.ended_at = datetime.now(timezone.utc)
            self.db.commit()
        self._invalidate_world_cache(payload.world_id)
        return {"ok": True, "emotion": state}

    def turn_begin(self, payload: SessionEventRequest) -> dict:
        engine = self._engine_for_world(payload.world_id)
        state = engine.on_chat_started(connector_id=payload.connector_id, session_id=payload.session_id)
        self._invalidate_world_cache(payload.world_id)
        return {"ok": True, "emotion": state}

    def turn_finish(self, payload: SessionEventRequest) -> dict:
        engine = self._engine_for_world(payload.world_id)
        state = engine.on_chat_ended(
            connector_id=payload.connector_id,
            session_id=payload.session_id,
            meaningful=payload.meaningful,
        )
        self._invalidate_world_cache(payload.world_id)
        return {"ok": True, "emotion": state}

    def dream_run(self, payload: DreamRunRequest) -> DreamRunResponse:
        engine = self._engine_for_world(payload.world_id)
        result = engine.ensure_due_dream(dream_date=payload.dream_date, force=payload.force)
        if result is None:
            latest = engine.latest_dream()
            if latest is None:
                result = {"created": False, "dream": {}}
            else:
                result = {"created": False, "dream": latest}
        self._invalidate_world_cache(payload.world_id)
        return DreamRunResponse(world_id=payload.world_id, created=bool(result["created"]), dream=result["dream"])

    def dream_latest(self, world_id: str) -> DreamLatestResponse:
        engine = self._engine_for_world(world_id)
        return DreamLatestResponse(world_id=world_id, dream=engine.latest_dream())

    def _engine_for_world(self, world_id: str) -> WorldRuntimeEngine:
        row = self._get_world_row(world_id)
        pack_row = self._get_pack_row(row.pack_id)
        pack = AgentPackConfig.model_validate(pack_row.config_json)
        overrides = WorldOverrides.model_validate(row.overrides_json or {})
        return WorldRuntimeEngine(Path(row.runtime_dir), pack, overrides)

    def _get_pack_row(self, pack_id: str) -> AgentPackRow:
        row = self.db.query(AgentPackRow).filter(AgentPackRow.pack_id == pack_id).one_or_none()
        if not row:
            raise KeyError(f"pack not found: {pack_id}")
        return row

    def _get_world_row(self, world_id: str) -> WorldInstanceRow:
        row = self.db.query(WorldInstanceRow).filter(WorldInstanceRow.world_id == world_id).one_or_none()
        if not row:
            raise KeyError(f"world not found: {world_id}")
        return row

    @staticmethod
    def _pack_response(row: AgentPackRow) -> PackResponse:
        return PackResponse(
            pack_id=row.pack_id,
            display_name=row.display_name,
            is_preset=row.is_preset,
            config=AgentPackConfig.model_validate(row.config_json),
        )

    @staticmethod
    def _world_response(row: WorldInstanceRow) -> WorldResponse:
        return WorldResponse(
            world_id=row.world_id,
            pack_id=row.pack_id,
            display_name=row.display_name,
            overrides=WorldOverrides.model_validate(row.overrides_json or {}),
        )

    def _cache_key(self, payload: ContextRequest) -> str:
        digest = hashlib.sha256(
            json.dumps(
                {
                    "world_id": payload.world_id,
                    "message": payload.user_message,
                    "connector_id": payload.connector_id,
                    "extra": payload.extra_blocks,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return f"lifeos:context:{payload.world_id}:{digest}"

    def _cache_get(self, key: str) -> dict | None:
        if not self._redis:
            return None
        raw = self._redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    def _cache_set(self, key: str, value: dict) -> None:
        if not self._redis:
            return
        self._redis.setex(key, settings.context_cache_ttl_seconds, json.dumps(value, ensure_ascii=False))

    def _invalidate_world_cache(self, world_id: str) -> None:
        if not self._redis:
            return
        for key in self._redis.scan_iter(match=f"lifeos:context:{world_id}:*", count=100):
            self._redis.delete(key)
