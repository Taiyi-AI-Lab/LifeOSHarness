from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_SEEDS = 300
MAX_DREAMS = 60
MAX_SUMMARY_CHARS = 140


def _now_ms() -> int:
    return int(time.time() * 1000)


def _compact_text(value: str, *, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    text = " ".join((value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


class DreamEngine:
    """Stores daily dream seeds and produces a small symbolic prompt block."""

    def __init__(
        self,
        file_path: Path,
        *,
        timezone_name: str = "Asia/Shanghai",
        llm_generator: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    ):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.timezone_name = timezone_name or "Asia/Shanghai"
        self.llm_generator = llm_generator
        try:
            self.timezone = ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            self.timezone_name = "Asia/Shanghai"
            self.timezone = ZoneInfo("Asia/Shanghai")
        self.state = self._load()
        self._persist()

    def record_interaction_seed(self, connector_id: str, user_message: str, *, now_ms: int | None = None) -> dict[str, Any]:
        return self.record_seed(
            kind="user_interaction",
            summary=user_message,
            connector_id=connector_id,
            now_ms=now_ms,
        )

    def record_session_seed(
        self,
        connector_id: str,
        event: str,
        *,
        session_id: str | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        label = "会话开始" if event == "start" else "会话结束"
        summary = f"{label}：{connector_id}"
        return self.record_seed(
            kind=f"session_{event}",
            summary=summary,
            connector_id=connector_id,
            source_id=f"session:{event}:{session_id}" if session_id else None,
            now_ms=now_ms,
        )

    def record_seed(
        self,
        *,
        kind: str,
        summary: str,
        connector_id: str | None = None,
        source_id: str | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        now_ms = now_ms if now_ms is not None else _now_ms()
        summary = _compact_text(summary)
        if not summary:
            summary = "一段没有留下明确内容的互动。"
        seed = {
            "kind": kind,
            "summary": summary,
            "connector_id": connector_id,
            "source_id": source_id,
            "created_at": now_ms,
            "local_date": self._local_date(now_ms),
        }
        if source_id:
            for existing in self.state["seeds"]:
                if existing.get("kind") == kind and existing.get("source_id") == source_id:
                    return existing
        self.state["seeds"].append(seed)
        self.state["seeds"] = self.state["seeds"][-MAX_SEEDS:]
        self._persist()
        return seed

    def ensure_due_dream(
        self,
        *,
        now_ms: int | None = None,
        dream_date: str | None = None,
        force: bool = False,
    ) -> dict[str, Any] | None:
        now_ms = now_ms if now_ms is not None else _now_ms()
        target_date = dream_date or self._due_dream_date(now_ms)
        if not target_date:
            return None
        existing = self._find_dream(target_date)
        if existing and not force:
            return {"created": False, "dream": existing}
        dream = self._build_dream(target_date, now_ms=now_ms)
        if existing:
            self.state["dreams"] = [item for item in self.state["dreams"] if item.get("dream_date") != target_date]
        self.state["dreams"].append(dream)
        self.state["dreams"] = self.state["dreams"][-MAX_DREAMS:]
        self._persist()
        return {"created": True, "dream": dream}

    def latest_dream(self) -> dict[str, Any] | None:
        dreams = self.state.get("dreams") or []
        if not dreams:
            return None
        return sorted(dreams, key=lambda item: item.get("dream_date", ""))[-1]

    def build_prompt_block(self) -> str:
        dream = self.latest_dream()
        if not dream:
            return ""
        return str(dream.get("prompt_block") or "")

    def _build_dream(self, dream_date: str, *, now_ms: int) -> dict[str, Any]:
        seeds = [seed for seed in self.state["seeds"] if seed.get("local_date") == dream_date]
        triggers = [seed["summary"] for seed in seeds if seed.get("summary")]
        if not triggers:
            triggers = ["没有明确事件，只留下一点模糊的情绪。"]
            emotional_tone = "模糊"
            title = "一段很轻的梦"
        else:
            emotional_tone = self._tone_for_triggers(triggers)
            title = self._title_for_triggers(triggers)
        fragments = self._fragments_for_triggers(triggers, has_events=bool(seeds))
        llm_dream = self._build_llm_dream(
            dream_date,
            now_ms=now_ms,
            triggers=triggers,
            title=title,
            emotional_tone=emotional_tone,
            has_events=bool(seeds),
        )
        if llm_dream:
            title = llm_dream["title"]
            emotional_tone = llm_dream["emotional_tone"]
            fragments = llm_dream["fragments"]
        dream = {
            "dream_date": dream_date,
            "generated_at": now_ms,
            "timezone": self.timezone_name,
            "title": title,
            "fragments": fragments,
            "emotional_tone": emotional_tone,
            "triggers": triggers[:8],
            "generation": "llm" if llm_dream else "rules",
        }
        dream["prompt_block"] = self._render_prompt_block(dream, has_events=bool(seeds))
        return dream

    def _build_llm_dream(
        self,
        dream_date: str,
        *,
        now_ms: int,
        triggers: list[str],
        title: str,
        emotional_tone: str,
        has_events: bool,
    ) -> dict[str, Any] | None:
        if not self.llm_generator or not has_events:
            return None
        try:
            result = self.llm_generator(
                {
                    "dream_date": dream_date,
                    "generated_at": now_ms,
                    "timezone": self.timezone_name,
                    "triggers": triggers[:8],
                    "fallback_title": title,
                    "fallback_emotional_tone": emotional_tone,
                }
            )
        except Exception:
            return None
        if not isinstance(result, dict):
            return None
        clean_title = _compact_text(str(result.get("title") or ""), max_chars=40)
        clean_tone = _compact_text(str(result.get("emotional_tone") or ""), max_chars=20)
        clean_fragments = [
            _compact_text(str(fragment), max_chars=90)
            for fragment in result.get("fragments") or []
            if str(fragment).strip()
        ][:4]
        if not clean_title or not clean_tone or not clean_fragments:
            return None
        return {
            "title": clean_title,
            "emotional_tone": clean_tone,
            "fragments": clean_fragments,
        }

    def _render_prompt_block(self, dream: dict[str, Any], *, has_events: bool) -> str:
        lines = [
            "<dream_context>",
            f"# 昨夜梦境（{dream['dream_date']}）",
            f"- 标题：{dream['title']}",
            f"- 情绪底色：{dream['emotional_tone']}",
            "- 梦境片段：",
        ]
        for fragment in dream["fragments"]:
            lines.append(f"  - {fragment}")
        lines.append("- 触发线索：")
        for trigger in dream["triggers"]:
            lines.append(f"  - {trigger}")
        if not has_events:
            lines.append("- 没有明确事件，所以这个梦只能作为模糊情绪，不能当成现实发生过的事。")
        lines.extend(
            [
                "- 梦境是象征、情绪整理和记忆残片，不等同现实事实。",
                "- 可以把梦作为语气、联想和关心用户的线索，但不要凭梦编造真实履历。",
                "</dream_context>",
            ]
        )
        return "\n".join(lines)

    def _fragments_for_triggers(self, triggers: list[str], *, has_events: bool) -> list[str]:
        if not has_events:
            return ["梦里像是在清晨醒来前听见很远的声音，醒后只剩一点轻轻的余温。"]
        fragments = []
        for trigger in triggers[:3]:
            fragments.append(f"梦里把「{trigger}」折成了一个安静的画面。")
        return fragments

    def _tone_for_triggers(self, triggers: list[str]) -> str:
        joined = " ".join(triggers)
        if any(word in joined for word in ["累", "烦", "压力", "难过", "痛"]):
            return "疲惫"
        if any(word in joined for word in ["开心", "顺利", "喜欢", "温柔"]):
            return "明亮"
        if any(word in joined for word in ["阿嬷", "信", "家", "想念"]):
            return "怀旧"
        return "平静"

    def _title_for_triggers(self, triggers: list[str]) -> str:
        first = triggers[0]
        if "阿嬷" in first or "信" in first:
            return "没寄出的信"
        if "代码" in first or "项目" in first:
            return "半夜还亮着的屏幕"
        return "昨日留下的回声"

    def _due_dream_date(self, now_ms: int) -> str | None:
        local_now = self._datetime(now_ms)
        if local_now.hour < 3:
            return None
        return (local_now.date() - timedelta(days=1)).isoformat()

    def _local_date(self, now_ms: int) -> str:
        return self._datetime(now_ms).date().isoformat()

    def _datetime(self, now_ms: int) -> datetime:
        return datetime.fromtimestamp(now_ms / 1000, tz=self.timezone)

    def _find_dream(self, dream_date: str) -> dict[str, Any] | None:
        for dream in self.state.get("dreams") or []:
            if dream.get("dream_date") == dream_date:
                return dream
        return None

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return {"seeds": [], "dreams": []}
        try:
            data = json.loads(self.file_path.read_text("utf-8"))
        except json.JSONDecodeError:
            return {"seeds": [], "dreams": []}
        if not isinstance(data, dict):
            return {"seeds": [], "dreams": []}
        return {
            "seeds": data.get("seeds") if isinstance(data.get("seeds"), list) else [],
            "dreams": data.get("dreams") if isinstance(data.get("dreams"), list) else [],
        }

    def _persist(self) -> None:
        self.file_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), "utf-8")
