from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "docs" / "modern-agent-pack-template.md"


def test_modern_agent_pack_template_documents_required_rules():
    content = TEMPLATE_PATH.read_text("utf-8")

    assert "人物提示词模板" in content
    assert "AgentPackConfig JSON 模板" in content
    assert "当前身份必须生活在现代真实世界" in content
    assert "非现代人物原型经历只能作为前世记忆" in content
    assert "不把前世经历说成当前现实经历" in content
    assert "最终输出同时给出" in content
    assert "【蛐蛐 · 内心独白】" in content
    assert "必须单独一行，以 ~> 开头" in content
    assert "一轮回复最多两句" in content
    assert "蛐蛐里提到用户时也要遵循称呼与性别感知规则" in content
    assert "未知性别时用名字或「对方」" in content
    assert "昨夜梦境" in content
    assert "梦境是象征、情绪整理和记忆残片" in content


def test_modern_agent_pack_template_json_matches_agent_pack_shape():
    content = TEMPLATE_PATH.read_text("utf-8")
    match = re.search(r"```json\n(?P<json>[\s\S]*?)\n```", content)

    assert match, "template must include one fenced JSON AgentPackConfig example"

    template_json = json.loads(match.group("json"))

    assert set(template_json) == {
        "pack_id",
        "display_name",
        "identity",
        "behavior_profile",
        "behavior_trajectory",
        "world_rules",
        "runtime_modules",
        "is_preset",
        "base_system_prompt",
    }
    assert template_json["base_system_prompt"] is None
    assert template_json["is_preset"] is False
    assert set(template_json["identity"]) == {
        "agent_name",
        "codename",
        "identity_code",
        "backstory",
        "relationship_stance",
        "core_values",
    }
    assert set(template_json["behavior_profile"]) == {
        "speech_style",
        "forbidden_patterns",
        "emotion_rules",
        "work_habits",
        "addressing_rules",
        "inner_voice_prompt",
    }
    assert set(template_json["behavior_trajectory"]) == {
        "milestones",
        "proactive_style",
        "reaction_patterns",
    }
    assert set(template_json["world_rules"]) == {
        "timezone",
        "work_hours",
        "locations",
        "custom_facts",
    }
    assert set(template_json["runtime_modules"]) == {
        "persona",
        "emotion",
        "memory",
        "world_facts",
        "proactive",
        "dreams",
    }


def test_musheng_pack_enables_dream_runtime_module():
    content = (ROOT / "docs" / "agent-packs" / "musheng.md").read_text("utf-8")

    assert "昨夜梦境" in content
    assert '"dreams": true' in content


def test_musheng_pack_documents_inner_monologue_rules():
    content = (ROOT / "docs" / "agent-packs" / "musheng.md").read_text("utf-8")

    assert "【蛐蛐 · 内心独白】" in content
    assert "~>又是侨批校对" in content
    assert "一轮回复最多两句" in content
    assert "蛐蛐里提到用户时也要遵循称呼与性别感知规则" in content
    assert "未知性别时用名字或「对方」" in content
    assert "蛐蛐不要使用 Markdown 引用块" in content
