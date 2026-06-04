from __future__ import annotations

import inspect
from pathlib import Path

from lifeostomanyagent.domain.models import (
    AgentPackConfig,
    RuntimeModules,
    WorldOverrides,
)
from lifeostomanyagent.server.engine import runtime as runtime_module
from lifeostomanyagent.server.presets.alice import build_alice_pack_config


def test_runtime_uses_embedded_state_modules():
    source = inspect.getsource(runtime_module)
    legacy_module = "bws" + "_fuxian"
    assert legacy_module not in source
    assert f"ensure_{legacy_module}_path" not in source
    assert "lifeostomanyagent.server.runtime_state" in source


def test_alice_structured_pack_has_identity():
    config = build_alice_pack_config()
    assert config["identity"]["agent_name"] == "Alice"
    assert config["identity"]["identity_code"] == "#76ACAD"
    assert config.get("base_system_prompt") is None
    assert "蛐蛐" in config["behavior_profile"]["inner_voice_prompt"]


def test_world_runtime_engine_builds_blocks(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime", pack, WorldOverrides())
    engine.on_chat_started()
    result = engine.build_context("你好", connector_id="hermes")
    assert "<agent_identity>" in result["system"]
    assert "<behavior_profile>" in result["system"]
    assert "蛐蛐" in result["system"]
    assert "<alice_persona>" in result["system"]
    assert "<alice_emotion>" in result["system"]
    assert "<user_message>" in result["system"]
    assert "# World Facts" in result["system"]
    assert "你好" in result["system"]
    assert "platform_guardrails" in result["order"]
    assert "agent_identity" in result["order"]
    assert "connector_overlay" not in result["order"]


def test_pi_includes_connector_overlay(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime_pi", pack, WorldOverrides())
    result = engine.build_context("你好", connector_id="pi")
    assert "connector_overlay" in result["order"]
    assert "todo_write" in result["system"] or "PptxGenJS" in result["system"]
    assert len(result["system"]) <= 28_500


def test_hermes_excludes_pi_tool_playbooks(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime_hermes", pack, WorldOverrides())
    hermes = engine.build_context("你好", connector_id="hermes")
    pi = engine.build_context("你好", connector_id="pi")
    assert len(hermes["system"]) < len(pi["system"])
    assert "PptxGenJS" not in hermes["system"]
    assert "novel_write" not in hermes["system"]
    assert "Alice" in hermes["system"]


def test_hermes_context_under_budget(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime_budget", pack, WorldOverrides())
    result = engine.build_context("你好", connector_id="hermes")
    assert len(result["system"]) <= 10_500
    assert "<context_compressed>" not in result["system"]


def test_legacy_base_system_prompt_pack(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig(
        pack_id="nova",
        display_name="Nova",
        base_system_prompt="你是 Nova，说话简短、有温度。",
    )
    engine = WorldRuntimeEngine(tmp_path / "runtime_nova", pack)
    result = engine.build_context("嗨", connector_id="hermes")
    assert "Nova" in result["system"]
    assert "<agent_identity>" in result["system"]


def test_session_events_update_emotion(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime2", pack)
    before = engine.emotion.state["loneliness"] if engine.emotion else None
    engine.on_chat_started()
    after_start = engine.emotion.state["loneliness"] if engine.emotion else None
    engine.on_chat_ended(meaningful=True)
    assert before is not None and after_start is not None
    assert after_start < before


def test_prompt_composer_protects_runtime_blocks(tmp_path: Path):
    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime_trim", pack)
    from lifeostomanyagent.server.engine import connector_profiles

    original = connector_profiles.CONNECTOR_PROFILES["hermes"]
    try:
        connector_profiles.CONNECTOR_PROFILES["hermes"] = type(original)(False, None, 800)
        result = engine.build_context("test", connector_id="hermes")
        assert "persona_state" in result["order"]
        assert "emotion_state" in result["order"]
        assert "user_message" in result["order"]
        assert "test" in result["system"]
    finally:
        connector_profiles.CONNECTOR_PROFILES["hermes"] = original


def test_dream_runtime_injects_latest_dream_after_emotion(tmp_path: Path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    def ms(year: int, month: int, day: int, hour: int) -> int:
        dt = datetime(year, month, day, hour, tzinfo=ZoneInfo("Asia/Shanghai"))
        return int(dt.timestamp() * 1000)

    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    pack.runtime_modules.dreams = True
    engine = WorldRuntimeEngine(tmp_path / "runtime_dream", pack, WorldOverrides())
    engine.record_interaction_seed(
        "hermes",
        "昨天聊到木生、阿嬷和一封没有寄出的信。",
        now=ms(2026, 6, 2, 22),
    )

    result = engine.build_context("早", connector_id="hermes", now=ms(2026, 6, 3, 3))

    assert "dream_context" in result["order"]
    assert result["order"].index("emotion_state") < result["order"].index("dream_context")
    assert result["order"].index("dream_context") < result["order"].index("user_message")
    assert "<dream_context>" in result["system"]
    assert "木生、阿嬷" in result["system"]


def test_dream_runtime_disabled_by_default(tmp_path: Path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine

    dt = datetime(2026, 6, 3, 3, tzinfo=ZoneInfo("Asia/Shanghai"))
    now = int(dt.timestamp() * 1000)
    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    pack.runtime_modules = RuntimeModules(dreams=False)
    engine = WorldRuntimeEngine(tmp_path / "runtime_no_dream", pack, WorldOverrides())

    result = engine.build_context("早", connector_id="hermes", now=now)

    assert "dream_context" not in result["order"]
    assert "<dream_context>" not in result["system"]
