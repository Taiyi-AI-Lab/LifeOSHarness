from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lifeostomanyagent.server.runtime_state.sql_store import SQLRuntimeStore

DEFAULT_STATE = {
    "mood": 58,
    "energy": 62,
    "socialNeed": 55,
    "affinity": 0,
    "trust": 0,
    "familiarity": 0,
    "location": "2035 年中国一座普通城市的出租屋",
    "statusTags": [],
    "relationshipStage": 1,
}


def _now() -> int:
    return int(time.time() * 1000)


def _clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


class PersonaSystem:
    def __init__(self, file_path: str | None = None, *, store: SQLRuntimeStore | None = None):
        self.store = store
        self.file_path = Path(file_path) if file_path else None
        if self.file_path:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load()
        self.state: dict[str, Any] = {**DEFAULT_STATE, **data.get("state", {})}
        self.interests: list[dict[str, Any]] = data.get("interests", [])
        self.journal: list[dict[str, Any]] = data.get("journal", [])
        self.relationship: dict[str, Any] = data.get(
            "relationship",
            {
                "stage": self.state["relationshipStage"],
                "address": "你",
                "lastInteractionAt": None,
            },
        )
        self._persist()

    def _load(self) -> dict[str, Any]:
        if self.store:
            return self.store.load_document("persona") or {}
        if not self.file_path or not self.file_path.exists():
            return {}
        try:
            data = json.loads(self.file_path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _persist(self) -> None:
        payload = {
            "state": self.state,
            "relationship": self.relationship,
            "interests": self.interests,
            "journal": self.journal,
        }
        if self.store:
            self.store.save_document("persona", payload)
            return
        if not self.file_path:
            return
        self.file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")

    def update_state(self, **changes: Any) -> dict[str, Any]:
        for key, value in changes.items():
            if key in {"mood", "energy", "socialNeed", "affinity", "trust", "familiarity"}:
                self.state[key] = _clamp(value)
            else:
                self.state[key] = value
        self.state["relationshipStage"] = self._relationship_stage()
        self.relationship["stage"] = self.state["relationshipStage"]
        self._persist()
        return dict(self.state)

    def apply_interaction(self, event_type: str, *, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else _now()
        if event_type == "meaningful_chat":
            self.state["affinity"] = _clamp(self.state["affinity"] + 3)
            self.state["trust"] = _clamp(self.state["trust"] + 2)
            self.state["familiarity"] = _clamp(self.state["familiarity"] + 4)
            self.state["mood"] = _clamp(self.state["mood"] + 2)
        elif event_type == "ignored":
            self.state["socialNeed"] = _clamp(self.state["socialNeed"] + 5)
            self.state["mood"] = _clamp(self.state["mood"] - 3)
        elif event_type == "conflict":
            self.state["trust"] = _clamp(self.state["trust"] - 5)
            self.state["mood"] = _clamp(self.state["mood"] - 8)
        self.relationship["lastInteractionAt"] = now
        self.state["relationshipStage"] = self._relationship_stage()
        self.relationship["stage"] = self.state["relationshipStage"]
        self._persist()
        return dict(self.state)

    def add_interest(
        self,
        interest_type: str,
        title: str,
        *,
        status: str = "active",
        note: str = "",
    ) -> dict[str, Any]:
        for interest in self.interests:
            if interest["type"] == interest_type and interest["title"] == title:
                interest.update({"status": status, "note": note})
                self._persist()
                return dict(interest)
        item = {
            "id": f"interest_{len(self.interests) + 1}",
            "type": interest_type,
            "title": title,
            "status": status,
            "note": note,
        }
        self.interests.append(item)
        self._persist()
        return dict(item)

    def record_journal(self, content: str, *, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else _now()
        entry = {
            "id": f"journal_{now}_{len(self.journal) + 1}",
            "content": content,
            "createdAt": now,
        }
        self.journal.append(entry)
        self.journal = self.journal[-50:]
        self._persist()
        return dict(entry)

    def build_persona_context(self, *, now: int | None = None) -> str:
        now = now if now is not None else _now()
        lines = [
            "<agent_persona>",
            "# Agent Persona",
            f"- mood: {self.state['mood']} ({_mood_label(self.state['mood'])})",
            f"- energy: {self.state['energy']}",
            f"- socialNeed: {self.state['socialNeed']}",
            f"- location: {self.state['location']}",
            f"- relationshipStage: {self.state['relationshipStage']}",
            f"- affinity/trust/familiarity: {self.state['affinity']}/{self.state['trust']}/{self.state['familiarity']}",
        ]
        if self.interests:
            lines.append("# Interests")
            for interest in self.interests[-8:]:
                note = f"：{interest['note']}" if interest.get("note") else ""
                lines.append(
                    f"- [{interest['type']}/{interest['status']}] {interest['title']}{note}"
                )
        if self.journal:
            lines.append("# Recent Journal")
            for entry in self.journal[-5:]:
                age = max(0, (now - int(entry["createdAt"])) // 60_000)
                lines.append(f"- {entry['content']}（{age} 分钟前）")
        lines.append("</agent_persona>")
        return "\n".join(lines)

    def _relationship_stage(self) -> int:
        score = self.state["affinity"] + self.state["trust"] + self.state["familiarity"]
        if score >= 210:
            return 5
        if score >= 150:
            return 4
        if score >= 90:
            return 3
        if score >= 30:
            return 2
        return 1


def _mood_label(value: int) -> str:
    if value >= 75:
        return "明亮"
    if value >= 50:
        return "平稳"
    if value >= 30:
        return "低落"
    return "脆弱"
