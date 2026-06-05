from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from lifeostomanyagent.config import settings
from lifeostomanyagent.server.engine.intent_classifier import IntentClassification

API_HEADERS = {"X-API-Key": "dev-lifeos-key-change-me"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chenyuan_preset_and_world_flow(client):
    preset = client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    assert preset.status_code == 200
    assert preset.json()["pack_id"] == "chenyuan"
    assert preset.json()["is_preset"] is True

    world = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "测试陈远"},
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
    assert "陈远" in body["system"]
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
    client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    world = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "turn test"},
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
    client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "connector diff"},
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


def test_context_skips_lifeos_for_task_by_default(client):
    client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "intent gate"},
    ).json()["world_id"]

    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "帮我修一下 pytest 报错",
            "connector_id": "claude-code",
        },
    )

    assert context.status_code == 200
    body = context.json()
    assert body["system"] == ""
    assert body["order"] == []
    assert body["blocks"] == []
    assert body["resolved_intent"] == "task"
    assert body["injected"] is False
    assert body["intent_classifier"] == "rules"


def test_context_injects_for_explicit_chitchat_override(client):
    client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "intent override"},
    ).json()["world_id"]

    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "帮我修一下 pytest 报错",
            "connector_id": "claude-code",
            "interaction_intent": "chitchat",
        },
    )

    assert context.status_code == 200
    body = context.json()
    assert "陈远" in body["system"]
    assert body["resolved_intent"] == "chitchat"
    assert body["injected"] is True
    assert body["intent_classifier"] == "explicit"


def test_context_uses_llm_classifier_when_configured(client, monkeypatch):
    calls: list[dict] = []

    class FakeIntentClassifier:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def classify(self, user_message: str):
            assert user_message == "帮我修一下 pytest 报错"
            return IntentClassification("chitchat", "llm", 0.99, "fake llm")

    monkeypatch.setattr(settings, "lifeos_intent_classifier", "llm")
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(settings, "deepseek_intent_model", "intent-model")
    monkeypatch.setattr(settings, "deepseek_intent_base_url", "https://intent.example")
    monkeypatch.setattr(
        "lifeostomanyagent.server.services.DeepSeekIntentClassifier",
        FakeIntentClassifier,
    )

    client.post("/packs/presets/chenyuan", headers=API_HEADERS)
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "chenyuan", "display_name": "intent llm"},
    ).json()["world_id"]

    context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "帮我修一下 pytest 报错",
            "connector_id": "claude-code",
        },
    )

    assert context.status_code == 200
    body = context.json()
    assert body["resolved_intent"] == "chitchat"
    assert body["intent_classifier"] == "llm"
    assert body["injected"] is True
    assert calls[0]["api_key"] == "test-key"
    assert calls[0]["model"] == "intent-model"
    assert calls[0]["base_url"] == "https://intent.example"


def test_dream_run_and_context_injection(client):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    created = client.post(
        "/packs",
        headers=API_HEADERS,
        json={
            "pack_id": "musheng-test",
            "display_name": "木生测试",
            "identity": {
                "agent_name": "木生",
                "codename": "musheng",
                "backstory": "现代生活中的木生。",
                "relationship_stance": "陪伴但有边界。",
                "core_values": ["诚实", "温柔", "记得重要的事"],
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
    assert created.status_code == 200
    world_id = client.post(
        "/worlds",
        headers=API_HEADERS,
        json={"pack_id": "musheng-test", "display_name": "木生测试世界"},
    ).json()["world_id"]

    first_context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "昨天我们聊了阿嬷的信，还有木生怎么在现代生活。",
            "connector_id": "hermes",
        },
    )
    assert first_context.status_code == 200

    dream = client.post(
        "/runtime/dreams/run",
        headers=API_HEADERS,
        json={"world_id": world_id, "dream_date": today, "force": True},
    )
    assert dream.status_code == 200
    assert dream.json()["created"] is True
    assert dream.json()["dream"]["dream_date"] == today

    second_context = client.post(
        "/runtime/context",
        headers=API_HEADERS,
        json={
            "world_id": world_id,
            "user_message": "早，昨晚梦见什么了吗？",
            "connector_id": "hermes",
        },
    ).json()
    assert "dream_context" in second_context["order"]
    assert "阿嬷的信" in second_context["system"]

    latest = client.get(f"/runtime/dreams/latest?world_id={world_id}", headers=API_HEADERS)
    assert latest.status_code == 200
    assert latest.json()["dream"]["dream_date"] == today
