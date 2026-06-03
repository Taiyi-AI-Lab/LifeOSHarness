from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from lifeostomanyagent.domain.models import AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.bootstrap import ensure_bws_fuxian_path


def _now_ms() -> int:
    return int(time.time() * 1000)


class WorldRuntimeEngine:
    """Assembles dynamic agent context from bws_fuxian state subsystems."""

    def __init__(self, world_root: Path, pack: AgentPackConfig, overrides: WorldOverrides | None = None):
        ensure_bws_fuxian_path()
        from bws_fuxian.emotion_system.system import AliceEmotionSystem
        from bws_fuxian.memory_system.system import UserMemorySystem
        from bws_fuxian.persona_system.system import AlicePersonaSystem
        from bws_fuxian.prompt_assembler.assembler import PromptAssembler
        from bws_fuxian.world_engine.engine import WorldEngine

        self.world_root = world_root
        self.pack = pack
        self.overrides = overrides or WorldOverrides()
        world_root.mkdir(parents=True, exist_ok=True)

        modules = pack.runtime_modules
        self.memory = UserMemorySystem(str(world_root / "memory")) if modules.memory else None
        self.persona = AlicePersonaSystem(str(world_root / "persona.json")) if modules.persona else None
        self.emotion = AliceEmotionSystem(str(world_root / "emotion.json")) if modules.emotion else None
        self.world = WorldEngine(str(world_root / "world.sqlite3")) if modules.world_facts else None
        self._assembler_cls = PromptAssembler

    def _base_system_prompt(self) -> str:
        prompt = self.pack.base_system_prompt.strip()
        append = self.overrides.base_system_prompt_append
        if append:
            prompt = f"{prompt}\n\n{append.strip()}"
        behavior = self._behavior_block()
        if behavior:
            prompt = f"{prompt}\n\n{behavior}"
        return prompt

    def _behavior_block(self) -> str:
        profile = self.pack.behavior_profile
        lines: list[str] = []
        if profile.speech_style:
            lines.append("【说话风格补充】")
            lines.extend(f"- {item}" for item in profile.speech_style)
        if profile.forbidden_patterns:
            lines.append("【禁止表达】")
            lines.extend(f"- {item}" for item in profile.forbidden_patterns)
        rules = self.pack.world_rules
        if rules.custom_facts or rules.locations:
            lines.append("【世界规则】")
            lines.append(f"- 时区: {rules.timezone}")
            lines.append(f"- 工作时间: {rules.work_hours}")
            for location in rules.locations:
                lines.append(f"- 地点: {location}")
            for fact in rules.custom_facts:
                lines.append(f"- {fact}")
        return "\n".join(lines).strip()

    def on_chat_started(self, *, now: int | None = None) -> dict[str, Any] | None:
        if not self.emotion:
            return None
        return self.emotion.apply_event("chat_started", now=now)

    def on_chat_ended(self, *, meaningful: bool = True, now: int | None = None) -> dict[str, Any] | None:
        if not self.emotion:
            return None
        return self.emotion.apply_event("chat_ended", meaningful=meaningful, now=now)

    def tick_emotion(self, *, now: int | None = None) -> dict[str, Any] | None:
        if not self.emotion:
            return None
        return self.emotion.tick(now=now)

    def build_context(
        self,
        user_message: str,
        *,
        connector_id: str = "generic",
        now: int | None = None,
        extra_blocks: list[str] | None = None,
    ) -> dict[str, Any]:
        now = now if now is not None else _now_ms()
        assembler = self._assembler_cls(
            base_system_prompt=self._base_system_prompt(),
            memory_system=self.memory,
            persona_system=self.persona,
            emotion_system=self.emotion,
            world_engine=self.world,
        )
        trace = assembler.assemble_with_trace(user_message, now=now, extra_blocks=extra_blocks)
        return {
            "connector_id": connector_id,
            "system": trace["prompt"],
            "order": trace["order"],
            "blocks": trace["blocks"],
        }
