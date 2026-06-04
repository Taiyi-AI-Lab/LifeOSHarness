from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from lifeostomanyagent.config import settings


class Base(DeclarativeBase):
    pass


class AgentPackRow(Base):
    __tablename__ = "agent_packs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pack_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    config_json: Mapped[dict] = mapped_column(JSON)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class WorldInstanceRow(Base):
    __tablename__ = "world_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    world_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    pack_id: Mapped[str] = mapped_column(String(128), index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    overrides_json: Mapped[dict] = mapped_column(JSON, default=dict)
    runtime_dir: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SessionRecordRow(Base):
    __tablename__ = "session_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    connector_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RuntimeStateDocumentRow(Base):
    __tablename__ = "runtime_state_documents"
    __table_args__ = (UniqueConstraint("world_id", "module", name="uq_runtime_state_world_module"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    module: Mapped[str] = mapped_column(String(64), index=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class UserMemoryRow(Base):
    __tablename__ = "user_memories"
    __table_args__ = (UniqueConstraint("world_id", "memory_id", name="uq_memory_world_memory_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    memory_id: Mapped[str] = mapped_column(String(128), index=True)
    memory_type: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at_ms: Mapped[int] = mapped_column(BigInteger)
    updated_at_ms: Mapped[int] = mapped_column(BigInteger)
    last_activated_at_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activation_count: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class MemorySnapshotRow(Base):
    __tablename__ = "memory_snapshots"
    __table_args__ = (
        UniqueConstraint("world_id", "snapshot_id", name="uq_memory_snapshot_world_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), index=True)
    label: Mapped[str] = mapped_column(String(256))
    entries_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at_ms: Mapped[int] = mapped_column(BigInteger)


class DreamSeedRow(Base):
    __tablename__ = "dream_seeds"
    __table_args__ = (
        UniqueConstraint("world_id", "kind", "source_id", name="uq_dream_seed_world_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text)
    connector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at_ms: Mapped[int] = mapped_column(BigInteger)
    local_date: Mapped[str] = mapped_column(String(16), index=True)


class DreamRecordRow(Base):
    __tablename__ = "dream_records"
    __table_args__ = (UniqueConstraint("world_id", "dream_date", name="uq_dream_world_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    dream_date: Mapped[str] = mapped_column(String(16), index=True)
    generated_at_ms: Mapped[int] = mapped_column(BigInteger)
    timezone: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(256))
    fragments_json: Mapped[list] = mapped_column(JSON, default=list)
    emotional_tone: Mapped[str] = mapped_column(String(64))
    triggers_json: Mapped[list] = mapped_column(JSON, default=list)
    generation: Mapped[str] = mapped_column(String(32), default="rules")
    prompt_block: Mapped[str] = mapped_column(Text)


class WorldFactRow(Base):
    __tablename__ = "world_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    subject: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    condition: Mapped[str] = mapped_column(String(64), default="正常")
    acquired_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    acquired_via: Mapped[str | None] = mapped_column(String(128), nullable=True)
    related_moment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    real_world_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class FactEventRow(Base):
    __tablename__ = "fact_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    fact_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class WorldClockEventRow(Base):
    __tablename__ = "world_clock_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    type: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str] = mapped_column(Text)
    trigger_at: Mapped[int] = mapped_column(BigInteger, index=True)
    fact_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    on_trigger: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    fired: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class VenueVisitRow(Base):
    __tablename__ = "venue_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    venue_name: Mapped[str] = mapped_column(Text, index=True)
    visited_at: Mapped[int] = mapped_column(BigInteger, index=True)
    spent: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class RuntimeMigrationRow(Base):
    __tablename__ = "runtime_migrations"
    __table_args__ = (
        UniqueConstraint("world_id", "source", name="uq_runtime_migration_world_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id: Mapped[str] = mapped_column(String(36), index=True)
    source: Mapped[str] = mapped_column(String(128), index=True)
    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


def _engine_kwargs(database_url: str) -> dict:
    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        database = url.database
        if database and database != ":memory:":
            Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    _engine_kwargs(settings.database_url)
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    return SessionLocal()
