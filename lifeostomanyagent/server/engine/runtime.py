from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from lifeostomanyagent.domain.models import AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.bootstrap import ensure_bws_fuxian_path
from lifeostomanyagent.server.engine.prompt_composer import PromptComposer


def _now_ms() -> int:
    return int(time.time() * 1000)


class WorldRuntimeEngine:
    """Assembles dynamic agent context from pack config and bws_fuxian state subsystems."""

    def __init__(self, world_root: Path, pack: AgentPackConfig, overrides: WorldOverrides | None = None):
        ensure_bws_fuxian_path()
        from bws_fuxian.emotion_system.system import AliceEmotionSystem
        from bws_fuxian.memory_system.system import UserMemorySystem
        from bws_fuxian.persona_system.system import AlicePersonaSystem
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
        composer = PromptComposer(
            pack=self.pack,
            overrides=self.overrides,
            memory_system=self.memory,
            persona_system=self.persona,
            emotion_system=self.emotion,
            world_engine=self.world,
        )
        return composer.compose(
            user_message,
            connector_id=connector_id,
            now=now,
            extra_blocks=extra_blocks,
        )
