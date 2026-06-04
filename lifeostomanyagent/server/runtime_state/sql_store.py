from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from lifeostomanyagent.server.db.models import (
    DreamRecordRow,
    DreamSeedRow,
    MemorySnapshotRow,
    RuntimeStateDocumentRow,
    UserMemoryRow,
)


class SQLRuntimeStore:
    def __init__(self, db: Session, world_id: str):
        self.db = db
        self.world_id = world_id

    def load_document(self, module: str) -> dict[str, Any] | None:
        row = self.db.scalar(
            select(RuntimeStateDocumentRow).where(
                RuntimeStateDocumentRow.world_id == self.world_id,
                RuntimeStateDocumentRow.module == module,
            )
        )
        return dict(row.state_json) if row else None

    def save_document(self, module: str, state: dict[str, Any]) -> None:
        row = self.db.scalar(
            select(RuntimeStateDocumentRow).where(
                RuntimeStateDocumentRow.world_id == self.world_id,
                RuntimeStateDocumentRow.module == module,
            )
        )
        if row is None:
            row = RuntimeStateDocumentRow(
                world_id=self.world_id,
                module=module,
                state_json=state,
            )
            self.db.add(row)
        else:
            row.state_json = state
            row.updated_at = datetime.now(UTC)
        self.db.commit()

    def load_memories(self) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(UserMemoryRow)
            .where(UserMemoryRow.world_id == self.world_id)
            .order_by(UserMemoryRow.created_at_ms.asc(), UserMemoryRow.memory_id.asc())
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

    def replace_memories(self, entries: list[dict[str, Any]]) -> None:
        self.db.execute(delete(UserMemoryRow).where(UserMemoryRow.world_id == self.world_id))
        for entry in entries:
            self.db.add(
                UserMemoryRow(
                    world_id=self.world_id,
                    memory_id=str(entry["id"]),
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
        self.db.commit()

    def save_memory_snapshot(
        self, label: str, entries: list[dict[str, Any]], *, created_at_ms: int
    ) -> dict[str, Any]:
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "snapshot"
        snapshot_id = f"{created_at_ms}-{safe_label}"
        row = MemorySnapshotRow(
            world_id=self.world_id,
            snapshot_id=snapshot_id,
            label=label,
            entries_json=entries,
            created_at_ms=created_at_ms,
        )
        self.db.add(row)
        self.db.commit()
        return {
            "label": label,
            "path": f"sql://memory_snapshots/{snapshot_id}",
            "createdAt": created_at_ms,
            "count": len(entries),
        }

    def load_memory_snapshot(self, snapshot_uri: str) -> list[dict[str, Any]]:
        snapshot_id = snapshot_uri.removeprefix("sql://memory_snapshots/")
        row = self.db.scalar(
            select(MemorySnapshotRow).where(
                MemorySnapshotRow.world_id == self.world_id,
                MemorySnapshotRow.snapshot_id == snapshot_id,
            )
        )
        if row is None:
            raise FileNotFoundError(snapshot_uri)
        return list(row.entries_json or [])

    def load_dream_state(self) -> dict[str, list[dict[str, Any]]]:
        seeds = self.db.scalars(
            select(DreamSeedRow)
            .where(DreamSeedRow.world_id == self.world_id)
            .order_by(DreamSeedRow.created_at_ms.asc(), DreamSeedRow.id.asc())
        ).all()
        dreams = self.db.scalars(
            select(DreamRecordRow)
            .where(DreamRecordRow.world_id == self.world_id)
            .order_by(DreamRecordRow.dream_date.asc(), DreamRecordRow.id.asc())
        ).all()
        return {
            "seeds": [
                {
                    "kind": row.kind,
                    "summary": row.summary,
                    "connector_id": row.connector_id,
                    "source_id": row.source_id,
                    "created_at": row.created_at_ms,
                    "local_date": row.local_date,
                }
                for row in seeds
            ],
            "dreams": [
                {
                    "dream_date": row.dream_date,
                    "generated_at": row.generated_at_ms,
                    "timezone": row.timezone,
                    "title": row.title,
                    "fragments": list(row.fragments_json or []),
                    "emotional_tone": row.emotional_tone,
                    "triggers": list(row.triggers_json or []),
                    "generation": row.generation,
                    "prompt_block": row.prompt_block,
                }
                for row in dreams
            ],
        }

    def replace_dream_state(self, state: dict[str, Any]) -> None:
        self.db.execute(delete(DreamSeedRow).where(DreamSeedRow.world_id == self.world_id))
        self.db.execute(delete(DreamRecordRow).where(DreamRecordRow.world_id == self.world_id))
        for seed in state.get("seeds") or []:
            self.db.add(
                DreamSeedRow(
                    world_id=self.world_id,
                    kind=str(seed.get("kind") or "unknown"),
                    summary=str(seed.get("summary") or ""),
                    connector_id=seed.get("connector_id"),
                    source_id=seed.get("source_id"),
                    created_at_ms=int(seed.get("created_at") or 0),
                    local_date=str(seed.get("local_date") or ""),
                )
            )
        for dream in state.get("dreams") or []:
            self.db.add(
                DreamRecordRow(
                    world_id=self.world_id,
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
        self.db.commit()
