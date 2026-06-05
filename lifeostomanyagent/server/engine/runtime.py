from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from lifeostomanyagent.config import settings
from lifeostomanyagent.domain.models import AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.dream_llm import DeepSeekDreamLLM
from lifeostomanyagent.server.engine.dreams import DreamEngine
from lifeostomanyagent.server.engine.prompt_composer import PromptComposer
from lifeostomanyagent.server.runtime_state.emotion_system.system import EmotionSystem
from lifeostomanyagent.server.runtime_state.memory_system.system import UserMemorySystem
from lifeostomanyagent.server.runtime_state.persona_system.system import PersonaSystem
from lifeostomanyagent.server.runtime_state.sql_store import SQLRuntimeStore
from lifeostomanyagent.server.runtime_state.world_engine.engine import WorldEngine


def _now_ms() -> int:
    return int(time.time() * 1000)


class WorldRuntimeEngine:
    """Assembles dynamic agent context from pack config and embedded runtime state subsystems."""

    def __init__(
        self,
        world_root: Path | None = None,
        pack: AgentPackConfig | None = None,
        overrides: WorldOverrides | None = None,
        *,
        db: Session | None = None,
        world_id: str | None = None,
    ):
        if pack is None:
            raise ValueError("pack is required")
        self.world_root = world_root
        self.pack = pack
        self.overrides = overrides or WorldOverrides()
        self.sql_store = (
            SQLRuntimeStore(db, world_id) if db is not None and world_id is not None else None
        )
        if world_root:
            world_root.mkdir(parents=True, exist_ok=True)

        modules = pack.runtime_modules
        self.memory = (
            UserMemorySystem(
                str(world_root / "memory") if world_root else None,
                store=self.sql_store,
            )
            if modules.memory
            else None
        )
        self.persona = (
            PersonaSystem(
                str(world_root / "persona.json") if world_root else None,
                store=self.sql_store,
            )
            if modules.persona
            else None
        )
        self.emotion = (
            EmotionSystem(
                str(world_root / "emotion.json") if world_root else None,
                store=self.sql_store,
            )
            if modules.emotion
            else None
        )
        self.world = (
            WorldEngine(
                str(world_root / "world.sqlite3") if world_root else "lifeos/world.sqlite3",
                db=db,
                world_id=world_id,
            )
            if modules.world_facts
            else None
        )
        self.dreams = (
            DreamEngine(
                world_root / "dreams.json" if world_root else None,
                timezone_name=pack.world_rules.timezone,
                llm_generator=self._dream_llm_generator(),
                store=self.sql_store,
            )
            if modules.dreams
            else None
        )

    def _dream_llm_generator(self) -> DeepSeekDreamLLM | None:
        api_key = (settings.deepseek_api_key or "").strip()
        if not api_key:
            return None
        return DeepSeekDreamLLM(
            api_key=api_key,
            model=settings.deepseek_dream_model,
            base_url=settings.deepseek_dream_base_url,
        )

    def on_chat_started(
        self,
        *,
        connector_id: str = "runtime",
        session_id: str | None = None,
        now: int | None = None,
    ) -> dict[str, Any] | None:
        if self.dreams:
            self.dreams.record_session_seed(
                connector_id, "start", session_id=session_id, now_ms=now
            )
        if not self.emotion:
            return None
        return self.emotion.apply_event("chat_started", now=now)

    def on_chat_ended(
        self,
        *,
        connector_id: str = "runtime",
        session_id: str | None = None,
        meaningful: bool = True,
        now: int | None = None,
    ) -> dict[str, Any] | None:
        if self.dreams:
            self.dreams.record_session_seed(connector_id, "end", session_id=session_id, now_ms=now)
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
        self.ensure_due_dream(now=now)
        composer = PromptComposer(
            pack=self.pack,
            overrides=self.overrides,
            memory_system=self.memory,
            persona_system=self.persona,
            emotion_system=self.emotion,
            world_engine=self.world,
            dream_engine=self.dreams,
        )
        result = composer.compose(
            user_message,
            connector_id=connector_id,
            now=now,
            extra_blocks=extra_blocks,
        )
        self.record_interaction_seed(connector_id, user_message, now=now)
        return result

    def ensure_due_dream(
        self,
        *,
        now: int | None = None,
        dream_date: str | None = None,
        force: bool = False,
    ) -> dict[str, Any] | None:
        if not self.dreams:
            return None
        now = now if now is not None else _now_ms()
        self._sync_external_dream_seeds(now=now)
        return self.dreams.ensure_due_dream(now_ms=now, dream_date=dream_date, force=force)

    def latest_dream(self) -> dict[str, Any] | None:
        if not self.dreams:
            return None
        return self.dreams.latest_dream()

    def record_interaction_seed(
        self, connector_id: str, user_message: str, *, now: int | None = None
    ) -> dict[str, Any] | None:
        if not self.dreams:
            return None
        return self.dreams.record_interaction_seed(connector_id, user_message, now_ms=now)

    def _sync_external_dream_seeds(self, *, now: int) -> None:
        if not self.dreams:
            return
        if self.persona:
            for entry in getattr(self.persona, "journal", [])[-10:]:
                content = str(entry.get("content") or "")
                created_at = int(entry.get("createdAt") or now)
                source_id = str(entry.get("id") or f"persona:{created_at}:{content[:16]}")
                self.dreams.record_seed(
                    kind="persona_journal",
                    summary=content,
                    source_id=source_id,
                    now_ms=created_at,
                )
        if self.emotion:
            state = getattr(self.emotion, "state", {})
            if state:
                summary = (
                    f"情绪状态：mood={state.get('mood')} energy={state.get('energy')} "
                    f"loneliness={state.get('loneliness')} stress={state.get('stress')}"
                )
                self.dreams.record_seed(
                    kind="emotion_state", summary=summary, source_id=f"emotion:{now}", now_ms=now
                )
        if self.world:
            try:
                events = self.world.store.get_recent_events(limit=10)
            except Exception:
                events = []
            for event in events:
                summary = str(event.get("subject") or event.get("content") or "")
                created_at = int(event.get("createdAt") or now)
                source_id = str(event.get("id") or f"world:{created_at}:{summary[:16]}")
                self.dreams.record_seed(
                    kind="world_event",
                    summary=summary,
                    source_id=source_id,
                    now_ms=created_at,
                )
