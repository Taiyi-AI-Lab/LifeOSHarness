from __future__ import annotations

from sqlalchemy import select

from lifeostomanyagent.server.db.models import FactEventRow, UserMemoryRow, WorldFactRow

API_HEADERS = {"X-API-Key": "dev-lifeos-key-change-me"}


def _create_world(client) -> str:
    client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    response = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "Inspector陈远"},
    )
    assert response.status_code == 200
    return response.json()["world_id"]


def test_inspector_state_requires_api_key(client):
    response = client.get("/inspector/worlds/missing/state")

    assert response.status_code == 401


def test_inspector_state_returns_404_for_missing_world(client):
    response = client.get("/inspector/worlds/missing/state", headers=API_HEADERS)

    assert response.status_code == 404


def test_inspector_state_returns_empty_runtime_sections_for_new_world(client):
    world_id = _create_world(client)

    response = client.get(f"/inspector/worlds/{world_id}/state", headers=API_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["world"]["world_id"] == world_id
    assert body["pack"]["pack_id"] == "chenyuan"
    assert body["persona"] is None
    assert body["emotion"] is None
    assert body["memories"] == []
    assert body["dreams"] == {"seeds": [], "dreams": []}
    assert body["world_facts"] == {
        "active": [],
        "all": [],
        "fact_events": [],
        "clock_events": [],
        "venue_visits": [],
    }


def test_inspector_state_returns_runtime_documents_memories_and_world_facts(client):
    import lifeostomanyagent.server.db.models as db_models

    world_id = _create_world(client)
    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "你好，今天想聊聊。",
            "connector_id": "hermes",
            "interaction_intent": "chitchat",
        },
    )
    assert context.status_code == 200

    with db_models.SessionLocal() as db:
        memory = UserMemoryRow(
            world_id=world_id,
            memory_id="mem-inspector",
            memory_type="identity",
            content="用户想要可视化 LifeOS runtime。",
            status="active",
            created_at_ms=1,
            updated_at_ms=3,
            last_activated_at_ms=3,
            activation_count=2,
            metadata_json={"source": "test"},
        )
        fact = WorldFactRow(
            world_id=world_id,
            category="home_item",
            subject="白色台灯",
            description="书桌上的台灯",
            status="active",
            condition="正常",
            acquired_at=1,
            acquired_via="test",
            related_moment_id=None,
            real_world_price=None,
            paid_price=None,
            delivery_at=None,
            expires_at=None,
            metadata_json={"room": "study"},
            created_at=1,
            updated_at=2,
        )
        db.add(memory)
        db.add(fact)
        db.commit()
        db.refresh(fact)
        db.add(
            FactEventRow(
                world_id=world_id,
                fact_id=fact.id,
                event_type="note",
                subject="擦干净了",
                created_at=4,
                metadata_json={"source": "test"},
            )
        )
        db.commit()

    response = client.get(f"/inspector/worlds/{world_id}/state?limit=10", headers=API_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["persona"]["state"]["mood"] >= 0
    assert body["emotion"]["mood"] >= 0
    assert body["memories"][0]["id"] == "mem-inspector"
    assert body["world_facts"]["active"][0]["subject"] == "白色台灯"
    assert body["world_facts"]["all"][0]["subject"] == "白色台灯"
    assert body["world_facts"]["fact_events"][0]["subject"] == "擦干净了"

    with db_models.SessionLocal() as db:
        stored_memory = db.scalar(
            select(UserMemoryRow).where(UserMemoryRow.memory_id == "mem-inspector")
        )
        assert stored_memory is not None
