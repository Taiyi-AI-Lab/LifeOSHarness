from __future__ import annotations

from pathlib import Path

from lifeostomanyagent.domain.models import AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.platform_guardrails import PLATFORM_GUARDRAILS


def render_agent_identity(pack: AgentPackConfig, overrides: WorldOverrides | None = None) -> str:
    if pack.identity is not None:
        identity = pack.identity
        lines = ["<agent_identity>", f"# {identity.agent_name}"]
        if identity.codename:
            lines.append(f"代号：{identity.codename}")
        if identity.identity_code:
            lines.append(f"身份编号：{identity.identity_code}")
        lines.append("")
        lines.append(identity.backstory.strip())
        if identity.relationship_stance.strip():
            lines.append("")
            lines.append(identity.relationship_stance.strip())
        if identity.core_values:
            lines.append("")
            lines.append("【核心价值】")
            lines.extend(f"- {item}" for item in identity.core_values)
        lines.append("</agent_identity>")
        text = "\n".join(lines)
    elif pack.base_system_prompt:
        text = "\n".join(["<agent_identity>", pack.base_system_prompt.strip(), "</agent_identity>"])
    else:
        text = ""

    append = (overrides.base_system_prompt_append if overrides else None) or ""
    if append.strip():
        text = f"{text}\n\n{append.strip()}" if text else append.strip()
    return text.strip()


def render_behavior_profile(pack: AgentPackConfig) -> str:
    profile = pack.behavior_profile
    lines: list[str] = []
    if profile.speech_style:
        lines.append("【说话风格】")
        lines.extend(f"- {item}" for item in profile.speech_style)
    if profile.forbidden_patterns:
        lines.append("【禁止表达】")
        lines.extend(f"- {item}" for item in profile.forbidden_patterns)
    if profile.work_habits:
        lines.append("【工作与生活习惯】")
        lines.extend(f"- {item}" for item in profile.work_habits)
    if profile.addressing_rules:
        lines.append("【称呼与性别感知】")
        lines.extend(f"- {item}" for item in profile.addressing_rules)
    if profile.inner_voice_prompt and profile.inner_voice_prompt.strip():
        lines.append("")
        lines.append(profile.inner_voice_prompt.strip())
    if profile.emotion_rules:
        lines.append("【情绪规则】")
        for key, value in profile.emotion_rules.items():
            lines.append(f"- {key}: {value}")
    if not lines:
        return ""
    return "\n".join(["<behavior_profile>", *lines, "</behavior_profile>"])


def render_behavior_trajectory(pack: AgentPackConfig) -> str:
    trajectory = pack.behavior_trajectory
    lines: list[str] = []
    if trajectory.proactive_style:
        lines.append(f"主动风格：{trajectory.proactive_style.strip()}")
    if trajectory.milestones:
        lines.append("【行为轨迹 / 里程碑】")
        lines.extend(f"- {item}" for item in trajectory.milestones)
    if trajectory.reaction_patterns:
        lines.append("【反应模式】")
        lines.extend(f"- {item}" for item in trajectory.reaction_patterns)
    if not lines:
        return ""
    return "\n".join(["<behavior_trajectory>", *lines, "</behavior_trajectory>"])


def render_world_rules(pack: AgentPackConfig) -> str:
    rules = pack.world_rules
    lines = [
        "<world_rules>",
        "【世界规则】",
        f"- 时区: {rules.timezone}",
        f"- 工作时间: {rules.work_hours}",
    ]
    for location in rules.locations:
        lines.append(f"- 地点: {location}")
    for fact in rules.custom_facts:
        lines.append(f"- {fact}")
    lines.append("</world_rules>")
    return "\n".join(lines)


def render_platform_guardrails() -> str:
    return "\n".join(["<platform_guardrails>", PLATFORM_GUARDRAILS, "</platform_guardrails>"])


def load_connector_overlay(overlay_key: str) -> str:
    overlay_dir = Path(__file__).resolve().parents[1] / "overlays"
    path = overlay_dir / f"{overlay_key}_tools.md"
    if not path.exists():
        return ""
    content = path.read_text("utf-8").strip()
    if not content:
        return ""
    return "\n".join(["<connector_overlay>", content, "</connector_overlay>"])
