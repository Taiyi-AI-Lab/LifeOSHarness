from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from lifeostomanyagent.config import default_database_url
from lifeostomanyagent.server.db.models import (
    DreamRecordRow,
    DreamSeedRow,
    FactEventRow,
    RuntimeStateDocumentRow,
    UserMemoryRow,
    WorldFactRow,
    WorldInstanceRow,
)

API_HEADERS = {"X-API-Key": "dev-lifeos-key-change-me"}


def _ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Asia/Shanghai"))
    return int(dt.timestamp() * 1000)


def test_default_database_url_uses_lifeos_data_root(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LIFEOS_DATA_ROOT", str(tmp_path / "lifeos-data"))

    assert (
        default_database_url()
        == f"sqlite+pysqlite:///{tmp_path / 'lifeos-data' / 'lifeos.sqlite3'}"
    )


def test_settings_default_database_url_uses_env_file_data_root(tmp_path: Path, monkeypatch):
    from lifeostomanyagent.config import Settings

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LIFEOS_DATA_ROOT", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"LIFEOS_DATA_ROOT={tmp_path / 'from-env-file'}\n", "utf-8")

    loaded = Settings(_env_file=env_file)

    assert (
        loaded.database_url == f"sqlite+pysqlite:///{tmp_path / 'from-env-file' / 'lifeos.sqlite3'}"
    )


def test_api_runtime_state_is_persisted_in_sql_tables(client):
    import lifeostomanyagent.server.db.models as db_models

    client.post(
        "/packs",
        headers=API_HEADERS,
        json={
            "pack_id": "sql-dreams",
            "display_name": "SQL Dreams",
            "identity": {
                "agent_name": "SQL Dreams",
                "codename": "sql-dreams",
                "backstory": "测试 SQL runtime 存储。",
                "relationship_stance": "稳定陪伴。",
                "core_values": ["一致性"],
            },
            "runtime_modules": {
                "persona": True,
                "emotion": True,
                "memory": True,
                "world_facts": True,
                "proactive": True,
                "dreams": True,
            },
        },
    )
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "sql-dreams", "display_name": "sql world"},
    ).json()["world_id"]

    client.post(
        "/runtime/session/start",
        headers=API_HEADERS,
        json={"world_id": world_id, "connector_id": "hermes", "session_id": "s1"},
    )
    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "我喜欢安静的早晨", "connector_id": "hermes"},
    )
    assert context.status_code == 200

    with db_models.SessionLocal() as db:
        modules = {
            row.module
            for row in db.scalars(
                select(RuntimeStateDocumentRow).where(RuntimeStateDocumentRow.world_id == world_id)
            )
        }
        assert {"persona", "emotion"} <= modules
        assert db.scalar(select(DreamSeedRow).where(DreamSeedRow.world_id == world_id)) is not None

        world = db.scalar(select(WorldInstanceRow).where(WorldInstanceRow.world_id == world_id))
        assert world is not None
        assert not (Path(world.runtime_dir) / "persona.json").exists()
        assert not (Path(world.runtime_dir) / "world.sqlite3").exists()


def test_world_facts_use_the_same_sql_database(client):
    import lifeostomanyagent.server.db.models as db_models

    client.post("/packs/presets/alice", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "alice", "display_name": "facts sql"},
    ).json()["world_id"]

    client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "你好", "connector_id": "hermes"},
    )

    with db_models.SessionLocal() as db:
        from lifeostomanyagent.server.services import LifeOSService

        world_engine = LifeOSService(db)._engine_for_world(world_id).world
        assert world_engine is not None
        created = world_engine.world_debug(
            "addFact",
            {"category": "home_item", "subject": "台灯", "description": "书桌上使用"},
        )
        assert created["ok"] is True
        event = world_engine.world_debug(
            "addFactEvent",
            {"factId": created["data"]["id"], "type": "note", "content": "擦干净了"},
        )
        assert event["ok"] is True

        assert db.scalar(select(WorldFactRow).where(WorldFactRow.world_id == world_id)) is not None
        assert db.scalar(select(FactEventRow).where(FactEventRow.world_id == world_id)) is not None


def test_legacy_runtime_files_are_imported_once(client, tmp_path: Path):
    import lifeostomanyagent.server.db.models as db_models

    client.post("/packs/presets/alice", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "alice", "display_name": "legacy import"},
    ).json()["world_id"]

    legacy_dir = tmp_path / "legacy-world"
    (legacy_dir / "memory" / "snapshots").mkdir(parents=True)
    (legacy_dir / "persona.json").write_text(
        json.dumps({"state": {"mood": 77}, "relationship": {}, "interests": [], "journal": []}),
        "utf-8",
    )
    (legacy_dir / "emotion.json").write_text(json.dumps({"mood": 41}), "utf-8")
    (legacy_dir / "memory" / "entries.json").write_text(
        json.dumps(
            [
                {
                    "id": "mem_1",
                    "type": "identity",
                    "content": "用户喜欢 SQLite 默认部署",
                    "status": "active",
                    "createdAt": 1,
                    "updatedAt": 2,
                    "lastActivatedAt": 2,
                    "activationCount": 3,
                    "metadata": {"source": "legacy"},
                }
            ],
            ensure_ascii=False,
        ),
        "utf-8",
    )
    (legacy_dir / "memory" / "snapshots" / "10-backup.json").write_text("[]", "utf-8")
    (legacy_dir / "dreams.json").write_text(
        json.dumps(
            {
                "seeds": [
                    {
                        "kind": "user_interaction",
                        "summary": "聊到旧数据迁移",
                        "connector_id": "hermes",
                        "source_id": "seed-1",
                        "created_at": _ms(2026, 6, 2, 20),
                        "local_date": "2026-06-02",
                    }
                ],
                "dreams": [
                    {
                        "dream_date": "2026-06-02",
                        "generated_at": _ms(2026, 6, 3, 3),
                        "timezone": "Asia/Shanghai",
                        "title": "旧库的梦",
                        "fragments": ["旧文件被搬进同一个数据库。"],
                        "emotional_tone": "平静",
                        "triggers": ["聊到旧数据迁移"],
                        "generation": "rules",
                        "prompt_block": "<dream_context>旧库的梦</dream_context>",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        "utf-8",
    )
    legacy_world_db = legacy_dir / "world.sqlite3"
    conn = sqlite3.connect(legacy_world_db)
    conn.executescript(
        """
        CREATE TABLE world_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            condition TEXT NOT NULL DEFAULT '正常',
            acquired_at INTEGER,
            acquired_via TEXT,
            related_moment_id TEXT,
            real_world_price INTEGER,
            paid_price INTEGER,
            delivery_at INTEGER,
            expires_at INTEGER,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        INSERT INTO world_facts (
            category, subject, description, status, condition, metadata_json, created_at, updated_at
        ) VALUES ('home_item', '旧台灯', '来自旧 sqlite', 'active', '正常', '{}', 1, 1);
        """
    )
    conn.commit()
    conn.close()

    with db_models.SessionLocal() as db:
        row = db.scalar(select(WorldInstanceRow).where(WorldInstanceRow.world_id == world_id))
        assert row is not None
        row.runtime_dir = str(legacy_dir)
        db.commit()

    response = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "早", "connector_id": "hermes"},
    )
    assert response.status_code == 200

    with db_models.SessionLocal() as db:
        assert (
            db.scalar(select(UserMemoryRow).where(UserMemoryRow.world_id == world_id)).content
            == "用户喜欢 SQLite 默认部署"
        )
        assert db.scalar(select(DreamSeedRow).where(DreamSeedRow.world_id == world_id)) is not None
        assert (
            db.scalar(select(DreamRecordRow).where(DreamRecordRow.world_id == world_id)).title
            == "旧库的梦"
        )
        assert (
            db.scalar(select(WorldFactRow).where(WorldFactRow.world_id == world_id)).subject
            == "旧台灯"
        )

    second = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "早", "connector_id": "hermes"},
    )
    assert second.status_code == 200

    with db_models.SessionLocal() as db:
        memories = db.scalars(select(UserMemoryRow).where(UserMemoryRow.world_id == world_id)).all()
        facts = db.scalars(select(WorldFactRow).where(WorldFactRow.world_id == world_id)).all()
        assert len(memories) == 1
        assert len(facts) == 1
