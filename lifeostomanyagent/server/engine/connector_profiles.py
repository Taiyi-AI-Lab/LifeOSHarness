from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorProfile:
    include_overlay: bool = False
    overlay_key: str | None = None
    max_chars: int = 10_000


CONNECTOR_PROFILES: dict[str, ConnectorProfile] = {
    "hermes": ConnectorProfile(include_overlay=False, max_chars=10_000),
    "claude-code": ConnectorProfile(include_overlay=False, max_chars=10_000),
    "claude_code": ConnectorProfile(include_overlay=False, max_chars=10_000),
    "claude": ConnectorProfile(include_overlay=False, max_chars=10_000),
    "codex": ConnectorProfile(include_overlay=False, max_chars=10_000),
    "openclaw": ConnectorProfile(include_overlay=False, max_chars=10_000),
    "pi": ConnectorProfile(include_overlay=True, overlay_key="pi", max_chars=28_000),
    "generic": ConnectorProfile(include_overlay=False, max_chars=10_000),
}

# Blocks trimmed first (highest trim priority) when over budget.
TRIM_PRIORITY: tuple[str, ...] = (
    "connector_overlay",
    "session_context",
    "extra_blocks",
    "behavior_trajectory",
    "behavior_profile",
    "agent_identity",
    "world_rules",
    "platform_guardrails",
)

# Never trim or drop these blocks.
PROTECTED_BLOCK_IDS: frozenset[str] = frozenset(
    {
        "persona_state",
        "emotion_state",
        "user_memory",
        "world_facts",
        "user_message",
    }
)


def get_connector_profile(connector_id: str) -> ConnectorProfile:
    return CONNECTOR_PROFILES.get(connector_id, CONNECTOR_PROFILES["generic"])
