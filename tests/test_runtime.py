from __future__ import annotations

from pathlib import Path

import pytest

from lifeostomanyagent.domain.models import AgentIdentity, AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.prompt_composer import PromptComposer
from lifeostomanyagent.server.presets.alice import build_alice_pack_config


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
