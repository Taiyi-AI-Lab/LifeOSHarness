from __future__ import annotations

API_HEADERS = {"X-API-Key": "dev-lifeos-key-change-me"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_alice_preset_and_world_flow(client):
    preset = client.post("/packs/presets/alice", headers=API_HEADERS)
    assert preset.status_code == 200
    assert preset.json()["pack_id"] == "alice"
    assert preset.json()["is_preset"] is True

    world = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "alice", "display_name": "测试 Alice"},
    )
    assert world.status_code == 200
    world_id = world.json()["world_id"]

    session = client.post(
        "/runtime/session/start",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "connector_id": "claude-code",
            "session_id": "sess-1",
        },
    )
    assert session.status_code == 200
    assert session.json()["ok"] is True

    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "今天有点累",
            "connector_id": "claude-code",
            "session_id": "sess-1",
        },
    )
    assert context.status_code == 200
    body = context.json()
    assert body["world_id"] == world_id
    assert "Alice" in body["system"]
    assert "今天有点累" in body["system"]
    assert "agent_identity" in body["order"]
    assert "connector_overlay" not in body["order"]

    ended = client.post(
        "/runtime/session/end",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "connector_id": "claude-code",
            "session_id": "sess-1",
            "meaningful": True,
        },
    )
    assert ended.status_code == 200
    assert ended.json()["ok"] is True


def test_turn_begin_and_finish(client):
    client.post("/packs/presets/alice", headers=API_HEADERS)
    world = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "alice", "display_name": "turn test"},
    ).json()
    world_id = world["world_id"]

    begin = client.post(
        "/runtime/turn/begin",
        headers=API_HEADERS,
        json={"world_id": world_id, "connector_id": "pi", "session_id": "pi-s1"},
    )
    assert begin.status_code == 200
    assert begin.json()["ok"] is True
    assert "emotion" in begin.json()

    finish = client.post(
        "/runtime/turn/finish",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "connector_id": "pi",
            "session_id": "pi-s1",
            "meaningful": True,
        },
    )
    assert finish.status_code == 200
    assert finish.json()["ok"] is True


def test_custom_pack(client):
    created = client.post(
        "/packs",
        headers=API_HEADERS,
        json={
            "pack_id": "nova",
            "display_name": "Nova",
            "base_system_prompt": "你是 Nova，说话简短、有温度。",
        },
    )
    assert created.status_code == 200

    world = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "nova", "display_name": "Nova 世界"},
    )
    world_id = world.json()["world_id"]

    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "嗨", "connector_id": "pi"},
    )
    assert context.status_code == 200
    assert "Nova" in context.json()["system"]


def test_pi_vs_hermes_context_size(client):
    client.post("/packs/presets/alice", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "alice", "display_name": "connector diff"},
    ).json()["world_id"]

    hermes = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "你好", "connector_id": "hermes"},
    ).json()
    pi = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={"world_id": world_id, "user_message": "你好", "connector_id": "pi"},
    ).json()

    assert len(hermes["system"]) < len(pi["system"])
    assert "connector_overlay" not in hermes["order"]
    assert "connector_overlay" in pi["order"]
    assert "PptxGenJS" not in hermes["system"]
    assert "todo_write" in pi["system"] or "PptxGenJS" in pi["system"]
