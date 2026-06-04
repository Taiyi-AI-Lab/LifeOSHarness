"""LifeOS Hermes plugin — inject Agent World context via pre_llm_call."""

from __future__ import annotations

from . import lifeos_client

CONNECTOR_ID = lifeos_client.CONNECTOR_ID
_active_turn_sessions: set[str] = set()


def _pre_llm_call(
    session_id: str, user_message: str, **kwargs
) -> dict[str, str] | None:
    del kwargs
    context = lifeos_client.fetch_context(CONNECTOR_ID, session_id, user_message or "")
    if not context:
        return None
    lifeos_client.turn_begin(CONNECTOR_ID, session_id)
    _active_turn_sessions.add(session_id)
    return {"context": context}


def _on_session_start(session_id: str, **kwargs) -> None:
    del kwargs
    lifeos_client.session_start(CONNECTOR_ID, session_id)


def _post_llm_call(session_id: str, **kwargs) -> None:
    del kwargs
    if session_id not in _active_turn_sessions:
        return
    lifeos_client.turn_finish(CONNECTOR_ID, session_id, meaningful=True)
    _active_turn_sessions.discard(session_id)


def _on_session_end(session_id: str, **kwargs) -> None:
    del kwargs
    _active_turn_sessions.discard(session_id)
    lifeos_client.session_end(CONNECTOR_ID, session_id, meaningful=True)


def register(ctx) -> None:
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("post_llm_call", _post_llm_call)
    ctx.register_hook("on_session_end", _on_session_end)
