from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterable
from typing import Any

from .prompts_world import WorldPrompts
from .store import WorldStore


class AliceFactExtractor:
    def __init__(
        self,
        store: WorldStore,
        *,
        enricher: Callable[[int], Any] | None = None,
        now: Callable[[], int] | None = None,
    ):
        self.store = store
        self.enricher = enricher
        self.now = now or (lambda: int(time.time() * 1000))

    def extract_alice_facts(self, messages: list[str], llm: Callable[[str], str]) -> list[dict[str, Any]]:
        if not messages:
            return []
        prompt = self.build_prompt(messages)
        try:
            response = llm(prompt)
            parsed = self._extract_json_array(response)
        except Exception:
            return []
        return [
            fact
            for fact in parsed
            if fact.get("subject") and fact.get("category") and fact.get("confidence") != "low"
        ]

    def commit_extracted_facts(self, facts: Iterable[dict[str, Any]]) -> int:
        count = 0
        for fact in facts:
            if self.find_similar_fact(fact.get("category"), fact.get("subject")):
                continue
            confidence = fact.get("confidence", "medium")
            added = self.store.add_fact(
                category=fact["category"],
                subject=fact["subject"],
                description=fact.get("description", ""),
                status="active" if confidence == "high" else "uncertain",
                condition="正常",
                acquired_at=self.now(),
                acquired_via="chat:extract",
                metadata={"confidence": confidence},
            )
            count += 1
            if self.enricher:
                self.enricher(added["id"])
        return count

    def find_similar_fact(self, category: str | None, subject: str | None) -> dict[str, Any] | None:
        if not category or not subject:
            return None
        normalized = _normalize(subject)
        for fact in self.store.get_all_facts():
            if fact["category"] == category and _normalize(fact["subject"]) == normalized:
                return fact
        return None

    @staticmethod
    def build_prompt(messages: list[str]) -> str:
        return WorldPrompts.fact_extract_prompt(messages)

    @staticmethod
    def _extract_json_array(text: str) -> list[dict[str, Any]]:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else []


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()
