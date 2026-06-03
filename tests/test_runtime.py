from __future__ import annotations

from pathlib import Path

import pytest

from lifeostomanyagent.domain.models import AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.runtime import WorldRuntimeEngine
from lifeostomanyagent.server.presets.alice import build_alice_pack_config, load_alice_system_prompt


def test_alice_system_prompt_loads():
    prompt = load_alice_system_prompt()
    assert "Alice" in prompt
    assert "#76ACAD" in prompt
    assert len(prompt) > 1000


def test_world_runtime_engine_builds_blocks(tmp_path: Path):
    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime", pack, WorldOverrides())
    engine.on_chat_started()
    result = engine.build_context("你好", connector_id="test")
    assert "<system>" in result["system"]
    assert "<alice_persona>" in result["system"]
    assert "<alice_emotion>" in result["system"]
    assert "<user_message>" in result["system"]
    assert "你好" in result["system"]
    assert "base_system" in result["order"]


def test_session_events_update_emotion(tmp_path: Path):
    pack = AgentPackConfig.model_validate(build_alice_pack_config())
    engine = WorldRuntimeEngine(tmp_path / "runtime2", pack)
    before = engine.emotion.state["loneliness"] if engine.emotion else None
    engine.on_chat_started()
    after_start = engine.emotion.state["loneliness"] if engine.emotion else None
    engine.on_chat_ended(meaningful=True)
    assert before is not None and after_start is not None
    assert after_start < before
