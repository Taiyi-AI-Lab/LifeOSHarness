from __future__ import annotations

from typing import Any

from lifeostomanyagent.domain.models import AgentPackConfig, WorldOverrides
from lifeostomanyagent.server.engine.connector_profiles import (
    PROTECTED_BLOCK_IDS,
    TRIM_PRIORITY,
    get_connector_profile,
)
from lifeostomanyagent.server.engine.pack_renderer import (
    load_connector_overlay,
    render_agent_identity,
    render_behavior_profile,
    render_behavior_trajectory,
    render_platform_guardrails,
    render_world_rules,
)


def _compact_block(content: str, max_len: int) -> str:
    if len(content) <= max_len:
        return content
    if max_len <= 80:
        return content[:max_len]
    head = max_len // 2
    tail = max_len - head - 40
    return content[:head] + "\n\n<trimmed>…内容因长度限制已截断…</trimmed>\n\n" + content[-tail:]


class PromptComposer:
    """Assemble connector-aware prompt blocks with priority-based trimming."""

    def __init__(
        self,
        *,
        pack: AgentPackConfig,
        overrides: WorldOverrides | None = None,
        memory_system: Any | None = None,
        persona_system: Any | None = None,
        emotion_system: Any | None = None,
        world_engine: Any | None = None,
        dream_engine: Any | None = None,
    ):
        self.pack = pack
        self.overrides = overrides or WorldOverrides()
        self.memory_system = memory_system
        self.persona_system = persona_system
        self.emotion_system = emotion_system
        self.world_engine = world_engine
        self.dream_engine = dream_engine

    def compose(
        self,
        user_message: str,
        *,
        connector_id: str = "generic",
        now: int | None = None,
        extra_blocks: list[str] | None = None,
    ) -> dict[str, Any]:
        profile = get_connector_profile(connector_id)
        blocks = self._collect_blocks(
            user_message,
            connector_id=connector_id,
            profile=profile,
            now=now,
            extra_blocks=extra_blocks,
        )
        blocks = self._apply_budget(blocks, profile.max_chars)
        prompt = "\n\n".join(block["content"] for block in blocks if block.get("content"))
        return {
            "connector_id": connector_id,
            "system": prompt,
            "order": [block["id"] for block in blocks],
            "blocks": [
                {"id": block["id"], "tag": block.get("tag"), "contentLength": len(block["content"])}
                for block in blocks
            ],
        }

    def _collect_blocks(
        self,
        user_message: str,
        *,
        connector_id: str,
        profile: Any,
        now: int | None,
        extra_blocks: list[str] | None,
    ) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []

        guardrails = render_platform_guardrails()
        if guardrails:
            blocks.append(
                {"id": "platform_guardrails", "tag": "<platform_guardrails>", "content": guardrails}
            )

        identity = render_agent_identity(self.pack, self.overrides)
        if identity:
            blocks.append({"id": "agent_identity", "tag": "<agent_identity>", "content": identity})

        behavior = render_behavior_profile(self.pack)
        if behavior:
            blocks.append(
                {"id": "behavior_profile", "tag": "<behavior_profile>", "content": behavior}
            )

        trajectory = render_behavior_trajectory(self.pack)
        if trajectory:
            blocks.append(
                {"id": "behavior_trajectory", "tag": "<behavior_trajectory>", "content": trajectory}
            )

        world_rules = render_world_rules(self.pack)
        if world_rules:
            blocks.append({"id": "world_rules", "tag": "<world_rules>", "content": world_rules})

        if self.persona_system:
            content = self.persona_system.build_persona_context(now=now)
            if content:
                blocks.append({"id": "persona_state", "tag": "<agent_persona>", "content": content})

        if self.emotion_system:
            content = self.emotion_system.build_emotion_prompt_block()
            if content:
                blocks.append({"id": "emotion_state", "tag": "<agent_emotion>", "content": content})

        if self.dream_engine:
            content = self.dream_engine.build_prompt_block()
            if content:
                blocks.append({"id": "dream_context", "tag": "<dream_context>", "content": content})

        if self.memory_system:
            content = self.memory_system.get_system_prompt_block()
            if content:
                blocks.append(
                    {"id": "user_memory", "tag": "<user_memory_update>", "content": content}
                )

        if self.world_engine:
            content = self.world_engine.build_world_facts_prompt_block(now=now)
            if content:
                blocks.append({"id": "world_facts", "tag": "# World Facts", "content": content})

        if profile.include_overlay and profile.overlay_key:
            overlay = load_connector_overlay(profile.overlay_key)
            if overlay:
                blocks.append(
                    {"id": "connector_overlay", "tag": "<connector_overlay>", "content": overlay}
                )

        for index, block in enumerate(extra_blocks or []):
            if block:
                blocks.append(
                    {
                        "id": "extra_blocks" if index == 0 else f"extra_blocks_{index}",
                        "tag": None,
                        "content": block,
                    }
                )

        blocks.append(
            {
                "id": "user_message",
                "tag": "<user_message>",
                "content": "\n".join(["<user_message>", user_message, "</user_message>"]),
            }
        )
        return blocks

    def _apply_budget(self, blocks: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
        working = [dict(block) for block in blocks]

        def total_len(items: list[dict[str, Any]]) -> int:
            return sum(len(item["content"]) for item in items)

        if total_len(working) <= max_chars:
            return working

        # Fit connector overlay into remaining budget before dropping other blocks.
        overlay_indices = [
            i for i, block in enumerate(working) if block["id"] == "connector_overlay"
        ]
        if overlay_indices:
            overlay_index = overlay_indices[0]
            overlay = working[overlay_index]
            base_len = total_len(
                [block for idx, block in enumerate(working) if idx != overlay_index]
            )
            available = max_chars - base_len
            if available >= 500:
                if len(overlay["content"]) > available:
                    working[overlay_index]["content"] = _compact_block(
                        overlay["content"], available
                    )
            else:
                working.pop(overlay_index)

        if total_len(working) <= max_chars:
            return working

        priority_index = {block_id: index for index, block_id in enumerate(TRIM_PRIORITY)}

        # Drop lowest-priority trimmable blocks entirely (connector_overlay first).
        while total_len(working) > max_chars:
            trimmable = [
                (index, block)
                for index, block in enumerate(working)
                if block["id"] not in PROTECTED_BLOCK_IDS
            ]
            if not trimmable:
                break
            drop_index, _ = min(trimmable, key=lambda item: priority_index.get(item[1]["id"], 999))
            working.pop(drop_index)
            if total_len(working) <= max_chars:
                return working

        # Compact remaining trimmable blocks from lowest priority upward.
        while total_len(working) > max_chars:
            trimmable = [
                (index, block)
                for index, block in enumerate(working)
                if block["id"] not in PROTECTED_BLOCK_IDS and len(block["content"]) > 200
            ]
            if not trimmable:
                break
            trim_index, block = min(
                trimmable, key=lambda item: priority_index.get(item[1]["id"], 999)
            )
            overflow = total_len(working) - max_chars
            new_len = max(200, len(block["content"]) - overflow)
            working[trim_index]["content"] = _compact_block(block["content"], new_len)
            if len(working[trim_index]["content"]) >= len(block["content"]):
                working.pop(trim_index)

        return working
