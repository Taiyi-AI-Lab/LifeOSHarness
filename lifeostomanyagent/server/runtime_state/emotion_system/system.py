from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DEFAULT_STATE = {
    "mood": 60,
    "energy": 65,
    "loneliness": 35,
    "stress": 25,
    "relationshipWarmth": 30,
    "lastTickAt": None,
}


def _now() -> int:
    return int(time.time() * 1000)


def _clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


class AliceEmotionSystem:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = {**DEFAULT_STATE, **self._load()}
        self._persist()

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return {}
        try:
            data = json.loads(self.file_path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _persist(self) -> None:
        self.file_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), "utf-8")

    def apply_event(self, event_type: str, *, now: int | None = None, **payload: Any) -> dict[str, Any]:
        now = now if now is not None else _now()
        if event_type == "chat_started":
            self.state["loneliness"] = _clamp(self.state["loneliness"] - 8)
            self.state["relationshipWarmth"] = _clamp(self.state["relationshipWarmth"] + 4)
        elif event_type == "chat_ended":
            meaningful = bool(payload.get("meaningful", True))
            self.state["mood"] = _clamp(self.state["mood"] + (4 if meaningful else -1))
        elif event_type == "income_received":
            self.state["stress"] = _clamp(self.state["stress"] - 6)
            self.state["mood"] = _clamp(self.state["mood"] + 3)
        elif event_type == "moment_liked":
            self.state["mood"] = _clamp(self.state["mood"] + 2)
            self.state["relationshipWarmth"] = _clamp(self.state["relationshipWarmth"] + 1)
        elif event_type == "moment_commented":
            self.state["mood"] = _clamp(self.state["mood"] + 4)
            self.state["loneliness"] = _clamp(self.state["loneliness"] - 5)
        elif event_type == "negative_interaction":
            self.state["mood"] = _clamp(self.state["mood"] - 12)
            self.state["stress"] = _clamp(self.state["stress"] + 10)
            self.state["relationshipWarmth"] = _clamp(self.state["relationshipWarmth"] - 4)
        elif event_type == "dayscript_executed":
            effects = payload.get("effects") or {}
            self.state["mood"] = _clamp(self.state["mood"] + int(effects.get("mood", 0)))
            self.state["energy"] = _clamp(self.state["energy"] + int(effects.get("energy", 0)))
        self.state["lastEventAt"] = now
        self._persist()
        return dict(self.state)

    def tick(self, *, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else _now()
        previous = self.state.get("lastTickAt") or now
        hours = max(0, (now - int(previous)) / 3_600_000)
        self.state["energy"] = _clamp(self.state["energy"] - hours * 1.5)
        self.state["loneliness"] = _clamp(self.state["loneliness"] + hours * 0.8)
        self.state["stress"] = _clamp(self.state["stress"] + hours * 0.3)
        self.state["lastTickAt"] = now
        self._persist()
        return dict(self.state)

    def get_behavior_constraints(self) -> dict[str, bool]:
        return {
            "avoid_teasing": self.state["mood"] < 55 or self.state["stress"] > 50,
            "prefer_short_replies": self.state["energy"] < 35,
            "seek_connection": self.state["loneliness"] > 65,
            "soften_tone": self.state["relationshipWarmth"] < 25,
        }

    def build_emotion_prompt_block(self) -> str:
        constraints = self.get_behavior_constraints()
        lines = [
            "<alice_emotion>",
            "# Alice Emotion",
            f"- mood: {self.state['mood']} ({_label(self.state['mood'])})",
            f"- energy: {self.state['energy']}",
            f"- loneliness: {self.state['loneliness']}",
            f"- stress: {self.state['stress']}",
            f"- relationshipWarmth: {self.state['relationshipWarmth']}",
            "# Behavior Constraints",
        ]
        for key, enabled in constraints.items():
            lines.append(f"- {key}: {str(enabled).lower()}")
        lines.append("</alice_emotion>")
        return "\n".join(lines)


def _label(value: int) -> str:
    if value >= 75:
        return "positive"
    if value >= 50:
        return "neutral"
    if value >= 30:
        return "low"
    return "fragile"
