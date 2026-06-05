from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from lifeostomanyagent.config import settings
from lifeostomanyagent.domain.models import (
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
from lifeostomanyagent.server.db.models import (
    AgentPackRow,
    DreamRecordRow,
    DreamSeedRow,
    FactEventRow,
    MemorySnapshotRow,
    RuntimeMigrationRow,
    RuntimeStateDocumentRow,
    SessionRecordRow,
    UserMemoryRow,
    VenueVisitRow,
    WorldClockEventRow,
    WorldFactRow,
    WorldInstanceRow,
)
from lifeostomanyagent.server.engine.intent_classifier import (
    DeepSeekIntentClassifier,
    IntentClassification,
    classify_intent,
)
from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine
from lifeostomanyagent.server.presets.chenyuan import build_chenyuan_pack_config
from lifeostomanyagent.server.runtime_state.sql_store import SQLRuntimeStore
from lifeostomanyagent.server.runtime_state.world_engine.store import SQLWorldStore

logger = logging.getLogger(__name__)


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

    def ensure_chenyuan_preset(self) -> PackResponse:
        config_json = build_chenyuan_pack_config()
        existing = (
            self.db.query(AgentPackRow).filter(AgentPackRow.pack_id == "chenyuan").one_or_none()
        )
        if existing:
            existing.config_json = config_json
            existing.display_name = "陈远"
            self.db.commit()
            self.db.refresh(existing)
            return self._pack_response(existing)
        row = AgentPackRow(
            id=str(uuid.uuid4()),
            pack_id="chenyuan",
            display_name="陈远",
            config_json=config_json,
            is_preset=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._pack_response(row)

    def create_pack(self, payload: PackCreateRequest) -> PackResponse:
        if (
            self.db.query(AgentPackRow)
            .filter(AgentPackRow.pack_id == payload.pack_id)
            .one_or_none()
        ):
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

    def inspect_world_state(self, world_id: str, *, limit: int = 100) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        world = self.get_world(world_id)
        pack = self.get_pack(world.pack_id)
        runtime_store = SQLRuntimeStore(self.db, world_id)
        world_store = SQLWorldStore(self.db, world_id)

        return {
            "world": world.model_dump(),
            "pack": pack.model_dump(),
            "persona": runtime_store.load_document("persona"),
            "emotion": runtime_store.load_document("emotion"),
            "memories": self._inspect_memories(world_id, limit),
            "dreams": runtime_store.load_dream_state(),
            "world_facts": {
                "active": world_store.get_active_facts()[:limit],
                "all": world_store.get_all_facts()[:limit],
                "fact_events": self._inspect_fact_events(world_id, limit),
                "clock_events": self._inspect_clock_events(world_id, limit),
                "venue_visits": self._inspect_venue_visits(world_id, limit),
            },
        }

    def build_context(self, payload: ContextRequest) -> ContextResponse:
        intent = self._classify_context_intent(payload)
        if intent.resolved_intent == "task":
            self._get_world_row(payload.world_id)
            return ContextResponse(
                world_id=payload.world_id,
                connector_id=payload.connector_id,
                system="",
                order=[],
                blocks=[],
                resolved_intent=intent.resolved_intent,
                injected=False,
                intent_classifier=intent.classifier,
                intent_reason=intent.reason,
            )

        engine = self._engine_for_world(payload.world_id)
        use_cache = not bool(engine.dreams)
        cache_key = self._cache_key(payload, intent)
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
                {
                    "id": block["id"],
                    "tag": block.get("tag"),
                    "content_length": block["contentLength"],
                }
                for block in result["blocks"]
            ],
            resolved_intent=intent.resolved_intent,
            injected=bool(result["system"]),
            intent_classifier=intent.classifier,
            intent_reason=intent.reason,
        )
        if use_cache:
            self._cache_set(cache_key, response.model_dump())
        return response

    def session_start(self, payload: SessionEventRequest) -> dict:
        from datetime import datetime

        engine = self._engine_for_world(payload.world_id)
        state = engine.on_chat_started(
            connector_id=payload.connector_id, session_id=payload.session_id
        )
        row = SessionRecordRow(
            world_id=payload.world_id,
            connector_id=payload.connector_id,
            session_id=payload.session_id,
            started_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.commit()
        self._invalidate_world_cache(payload.world_id)
        return {"ok": True, "emotion": state}

    def session_end(self, payload: SessionEventRequest) -> dict:
        from datetime import datetime

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
            record.ended_at = datetime.now(UTC)
            self.db.commit()
        self._invalidate_world_cache(payload.world_id)
        return {"ok": True, "emotion": state}

    def turn_begin(self, payload: SessionEventRequest) -> dict:
        engine = self._engine_for_world(payload.world_id)
        state = engine.on_chat_started(
            connector_id=payload.connector_id, session_id=payload.session_id
        )
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
        return DreamRunResponse(
            world_id=payload.world_id,
            created=bool(result["created"]),
            dream=result["dream"],
        )

    def dream_latest(self, world_id: str) -> DreamLatestResponse:
        engine = self._engine_for_world(world_id)
        return DreamLatestResponse(world_id=world_id, dream=engine.latest_dream())

    def _inspect_memories(self, world_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(UserMemoryRow)
            .where(UserMemoryRow.world_id == world_id)
            .order_by(UserMemoryRow.updated_at_ms.desc(), UserMemoryRow.memory_id.asc())
            .limit(limit)
        ).all()
        return [
            {
                "id": row.memory_id,
                "type": row.memory_type,
                "content": row.content,
                "status": row.status,
                "createdAt": row.created_at_ms,
                "updatedAt": row.updated_at_ms,
                "lastActivatedAt": row.last_activated_at_ms,
                "activationCount": row.activation_count,
                "metadata": dict(row.metadata_json or {}),
            }
            for row in rows
        ]

    def _inspect_fact_events(self, world_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(FactEventRow)
            .where(FactEventRow.world_id == world_id)
            .order_by(FactEventRow.created_at.desc(), FactEventRow.id.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": row.id,
                "factId": row.fact_id,
                "eventType": row.event_type,
                "subject": row.subject,
                "createdAt": row.created_at,
                "metadata": dict(row.metadata_json or {}),
            }
            for row in rows
        ]

    def _inspect_clock_events(self, world_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(WorldClockEventRow)
            .where(WorldClockEventRow.world_id == world_id)
            .order_by(WorldClockEventRow.trigger_at.desc(), WorldClockEventRow.id.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": row.id,
                "type": row.type,
                "subject": row.subject,
                "triggerAt": row.trigger_at,
                "factId": row.fact_id,
                "onTrigger": row.on_trigger,
                "payload": dict(row.payload_json or {}),
                "fired": row.fired,
                "createdAt": row.created_at,
                "updatedAt": row.updated_at,
            }
            for row in rows
        ]

    def _inspect_venue_visits(self, world_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(VenueVisitRow)
            .where(VenueVisitRow.world_id == world_id)
            .order_by(VenueVisitRow.visited_at.desc(), VenueVisitRow.id.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": row.id,
                "venueName": row.venue_name,
                "visitedAt": row.visited_at,
                "spent": row.spent,
                "rating": row.rating,
                "note": row.note,
                "metadata": dict(row.metadata_json or {}),
            }
            for row in rows
        ]

    def _engine_for_world(self, world_id: str) -> WorldRuntimeEngine:
        row = self._get_world_row(world_id)
        self._import_legacy_runtime(row)
        pack_row = self._get_pack_row(row.pack_id)
        pack = AgentPackConfig.model_validate(pack_row.config_json)
        overrides = WorldOverrides.model_validate(row.overrides_json or {})
        return WorldRuntimeEngine(pack=pack, overrides=overrides, db=self.db, world_id=row.world_id)

    def _import_legacy_runtime(self, row: WorldInstanceRow) -> None:
        runtime_dir = Path(row.runtime_dir)
        if not runtime_dir.exists():
            return
        self._import_legacy_document(row.world_id, "persona", runtime_dir / "persona.json")
        self._import_legacy_document(row.world_id, "emotion", runtime_dir / "emotion.json")
        self._import_legacy_memory(row.world_id, runtime_dir / "memory")
        self._import_legacy_dreams(row.world_id, runtime_dir / "dreams.json")
        self._import_legacy_world_sqlite(row.world_id, runtime_dir / "world.sqlite3")

    def _import_legacy_document(self, world_id: str, module: str, path: Path) -> None:
        source = f"legacy:{module}"
        if self._migration_done(world_id, source) or not path.exists():
            return
        data = self._read_legacy_json(path)
        if not isinstance(data, dict):
            self._mark_migration(world_id, source)
            return
        row = (
            self.db.query(RuntimeStateDocumentRow)
            .filter(
                RuntimeStateDocumentRow.world_id == world_id,
                RuntimeStateDocumentRow.module == module,
            )
            .one_or_none()
        )
        if row is None:
            self.db.add(
                RuntimeStateDocumentRow(
                    world_id=world_id,
                    module=module,
                    state_json=data,
                )
            )
        self._mark_migration(world_id, source, commit=False)
        self.db.commit()

    def _import_legacy_memory(self, world_id: str, memory_dir: Path) -> None:
        source = "legacy:memory"
        if self._migration_done(world_id, source) or not memory_dir.exists():
            return
        entries = self._read_legacy_json(memory_dir / "entries.json")
        if isinstance(entries, list):
            existing_ids = {
                row.memory_id
                for row in self.db.query(UserMemoryRow.memory_id)
                .filter(UserMemoryRow.world_id == world_id)
                .all()
            }
            for entry in entries:
                if not isinstance(entry, dict) or str(entry.get("id")) in existing_ids:
                    continue
                self.db.add(
                    UserMemoryRow(
                        world_id=world_id,
                        memory_id=str(entry.get("id")),
                        memory_type=str(entry.get("type") or "identity"),
                        content=str(entry.get("content") or ""),
                        status=str(entry.get("status") or "active"),
                        created_at_ms=int(entry.get("createdAt") or 0),
                        updated_at_ms=int(entry.get("updatedAt") or entry.get("createdAt") or 0),
                        last_activated_at_ms=entry.get("lastActivatedAt"),
                        activation_count=int(entry.get("activationCount") or 1),
                        metadata_json=entry.get("metadata")
                        if isinstance(entry.get("metadata"), dict)
                        else {},
                    )
                )
        snapshots_dir = memory_dir / "snapshots"
        if snapshots_dir.exists():
            for path in sorted(snapshots_dir.glob("*.json")):
                snapshot_entries = self._read_legacy_json(path)
                if not isinstance(snapshot_entries, list):
                    continue
                snapshot_id = path.stem
                if (
                    self.db.query(MemorySnapshotRow)
                    .filter(
                        MemorySnapshotRow.world_id == world_id,
                        MemorySnapshotRow.snapshot_id == snapshot_id,
                    )
                    .one_or_none()
                ):
                    continue
                created_at = _leading_int(snapshot_id)
                self.db.add(
                    MemorySnapshotRow(
                        world_id=world_id,
                        snapshot_id=snapshot_id,
                        label=snapshot_id,
                        entries_json=snapshot_entries,
                        created_at_ms=created_at,
                    )
                )
        self._mark_migration(world_id, source, commit=False)
        self.db.commit()

    def _import_legacy_dreams(self, world_id: str, path: Path) -> None:
        source = "legacy:dreams"
        if self._migration_done(world_id, source) or not path.exists():
            return
        data = self._read_legacy_json(path)
        if not isinstance(data, dict):
            self._mark_migration(world_id, source)
            return
        for seed in data.get("seeds") or []:
            if not isinstance(seed, dict):
                continue
            self.db.add(
                DreamSeedRow(
                    world_id=world_id,
                    kind=str(seed.get("kind") or "unknown"),
                    summary=str(seed.get("summary") or ""),
                    connector_id=seed.get("connector_id"),
                    source_id=seed.get("source_id"),
                    created_at_ms=int(seed.get("created_at") or 0),
                    local_date=str(seed.get("local_date") or ""),
                )
            )
        for dream in data.get("dreams") or []:
            if not isinstance(dream, dict):
                continue
            if (
                self.db.query(DreamRecordRow)
                .filter(
                    DreamRecordRow.world_id == world_id,
                    DreamRecordRow.dream_date == str(dream.get("dream_date") or ""),
                )
                .one_or_none()
            ):
                continue
            self.db.add(
                DreamRecordRow(
                    world_id=world_id,
                    dream_date=str(dream.get("dream_date") or ""),
                    generated_at_ms=int(dream.get("generated_at") or 0),
                    timezone=str(dream.get("timezone") or "Asia/Shanghai"),
                    title=str(dream.get("title") or ""),
                    fragments_json=list(dream.get("fragments") or []),
                    emotional_tone=str(dream.get("emotional_tone") or ""),
                    triggers_json=list(dream.get("triggers") or []),
                    generation=str(dream.get("generation") or "rules"),
                    prompt_block=str(dream.get("prompt_block") or ""),
                )
            )
        self._mark_migration(world_id, source, commit=False)
        self.db.commit()

    def _import_legacy_world_sqlite(self, world_id: str, path: Path) -> None:
        source = "legacy:world_sqlite"
        if self._migration_done(world_id, source) or not path.exists():
            return
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as error:
            logger.warning("failed to open legacy world sqlite %s: %s", path, error)
            self._mark_migration(world_id, source)
            return
        try:
            fact_id_map = self._import_legacy_world_facts(world_id, conn)
            self._import_legacy_fact_events(world_id, conn, fact_id_map)
            self._import_legacy_clock_events(world_id, conn, fact_id_map)
            self._import_legacy_venue_visits(world_id, conn)
        finally:
            conn.close()
        self._mark_migration(world_id, source, commit=False)
        self.db.commit()

    def _import_legacy_world_facts(self, world_id: str, conn: sqlite3.Connection) -> dict[int, int]:
        fact_id_map: dict[int, int] = {}
        if not _table_exists(conn, "world_facts"):
            return fact_id_map
        rows = conn.execute("SELECT * FROM world_facts ORDER BY id").fetchall()
        for legacy in rows:
            row = WorldFactRow(
                world_id=world_id,
                category=legacy["category"],
                subject=legacy["subject"],
                description=legacy["description"],
                status=legacy["status"],
                condition=legacy["condition"],
                acquired_at=legacy["acquired_at"],
                acquired_via=legacy["acquired_via"],
                related_moment_id=legacy["related_moment_id"],
                real_world_price=legacy["real_world_price"],
                paid_price=legacy["paid_price"],
                delivery_at=legacy["delivery_at"],
                expires_at=legacy["expires_at"],
                metadata_json=_loads_json_object(legacy["metadata_json"]),
                created_at=legacy["created_at"],
                updated_at=legacy["updated_at"],
            )
            self.db.add(row)
            self.db.flush()
            fact_id_map[int(legacy["id"])] = int(row.id)
        return fact_id_map

    def _import_legacy_fact_events(
        self, world_id: str, conn: sqlite3.Connection, fact_id_map: dict[int, int]
    ) -> None:
        if not _table_exists(conn, "fact_events"):
            return
        for legacy in conn.execute("SELECT * FROM fact_events ORDER BY id").fetchall():
            legacy_fact_id = legacy["fact_id"]
            self.db.add(
                FactEventRow(
                    world_id=world_id,
                    fact_id=fact_id_map.get(int(legacy_fact_id)) if legacy_fact_id else None,
                    event_type=legacy["event_type"],
                    subject=legacy["subject"],
                    created_at=legacy["created_at"],
                    metadata_json=_loads_json_object(legacy["metadata_json"]),
                )
            )

    def _import_legacy_clock_events(
        self, world_id: str, conn: sqlite3.Connection, fact_id_map: dict[int, int]
    ) -> None:
        if not _table_exists(conn, "world_pending_events"):
            return
        for legacy in conn.execute("SELECT * FROM world_pending_events ORDER BY id").fetchall():
            legacy_fact_id = legacy["fact_id"]
            self.db.add(
                WorldClockEventRow(
                    world_id=world_id,
                    type=legacy["type"],
                    subject=legacy["subject"],
                    trigger_at=legacy["trigger_at"],
                    fact_id=fact_id_map.get(int(legacy_fact_id)) if legacy_fact_id else None,
                    on_trigger=legacy["on_trigger"],
                    payload_json=_loads_json_object(legacy["payload_json"]),
                    fired=bool(legacy["fired"]),
                    created_at=legacy["created_at"],
                    updated_at=legacy["updated_at"],
                )
            )

    def _import_legacy_venue_visits(self, world_id: str, conn: sqlite3.Connection) -> None:
        if not _table_exists(conn, "venue_visits"):
            return
        for legacy in conn.execute("SELECT * FROM venue_visits ORDER BY id").fetchall():
            self.db.add(
                VenueVisitRow(
                    world_id=world_id,
                    venue_name=legacy["venue_name"],
                    visited_at=legacy["visited_at"],
                    spent=legacy["spent"],
                    rating=legacy["rating"],
                    note=legacy["note"],
                    metadata_json=_loads_json_object(legacy["metadata_json"]),
                )
            )

    def _read_legacy_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("failed to import legacy json %s: %s", path, error)
            return None

    def _migration_done(self, world_id: str, source: str) -> bool:
        return (
            self.db.query(RuntimeMigrationRow)
            .filter(
                RuntimeMigrationRow.world_id == world_id,
                RuntimeMigrationRow.source == source,
            )
            .one_or_none()
            is not None
        )

    def _mark_migration(self, world_id: str, source: str, *, commit: bool = True) -> None:
        if not self._migration_done(world_id, source):
            self.db.add(
                RuntimeMigrationRow(
                    world_id=world_id,
                    source=source,
                    migrated_at=datetime.now(UTC),
                )
            )
        if commit:
            self.db.commit()

    def _get_pack_row(self, pack_id: str) -> AgentPackRow:
        row = self.db.query(AgentPackRow).filter(AgentPackRow.pack_id == pack_id).one_or_none()
        if not row:
            raise KeyError(f"pack not found: {pack_id}")
        return row

    def _get_world_row(self, world_id: str) -> WorldInstanceRow:
        row = (
            self.db.query(WorldInstanceRow)
            .filter(WorldInstanceRow.world_id == world_id)
            .one_or_none()
        )
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

    def _classify_context_intent(self, payload: ContextRequest) -> IntentClassification:
        llm_classifier = None
        if (
            payload.interaction_intent == "auto"
            and settings.lifeos_intent_classifier.strip().lower() == "llm"
        ):
            api_key = (settings.deepseek_api_key or "").strip()
            if api_key:
                llm_classifier = DeepSeekIntentClassifier(
                    api_key=api_key,
                    model=settings.deepseek_intent_model,
                    base_url=settings.intent_base_url,
                    timeout_seconds=settings.lifeos_intent_timeout_seconds,
                )
        return classify_intent(
            payload.user_message,
            requested_intent=payload.interaction_intent,
            llm_classifier=llm_classifier,
        )

    def _cache_key(self, payload: ContextRequest, intent: IntentClassification) -> str:
        digest = hashlib.sha256(
            json.dumps(
                {
                    "world_id": payload.world_id,
                    "message": payload.user_message,
                    "connector_id": payload.connector_id,
                    "interaction_intent": payload.interaction_intent,
                    "resolved_intent": intent.resolved_intent,
                    "intent_classifier": intent.classifier,
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
        self._redis.setex(
            key,
            settings.context_cache_ttl_seconds,
            json.dumps(value, ensure_ascii=False),
        )

    def _invalidate_world_cache(self, world_id: str) -> None:
        if not self._redis:
            return
        for key in self._redis.scan_iter(match=f"lifeos:context:{world_id}:*", count=100):
            self._redis.delete(key)


def _loads_json_object(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _leading_int(value: str) -> int:
    digits = []
    for char in value:
        if char.isdigit():
            digits.append(char)
        else:
            break
    return int("".join(digits) or 0)
