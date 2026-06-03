from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lifeostomanyagent.server.engine.dreams import DreamEngine


def _ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Asia/Shanghai"))
    return int(dt.timestamp() * 1000)


def test_dream_engine_waits_until_three_am(tmp_path: Path):
    engine = DreamEngine(tmp_path / "dreams.json", timezone_name="Asia/Shanghai")
    engine.record_interaction_seed(
        "hermes",
        "昨天一起聊了郑木生和阿嬷的信。",
        now_ms=_ms(2026, 6, 2, 21),
    )

    before_three = engine.ensure_due_dream(now_ms=_ms(2026, 6, 3, 2, 59))

    assert before_three is None
    assert engine.latest_dream() is None


def test_dream_engine_generates_yesterday_once_after_three_am(tmp_path: Path):
    engine = DreamEngine(tmp_path / "dreams.json", timezone_name="Asia/Shanghai")
    engine.record_interaction_seed(
        "hermes",
        "昨天一起聊了郑木生和阿嬷的信。",
        now_ms=_ms(2026, 6, 2, 21),
    )

    first = engine.ensure_due_dream(now_ms=_ms(2026, 6, 3, 3, 1))
    second = engine.ensure_due_dream(now_ms=_ms(2026, 6, 3, 3, 2))

    assert first is not None
    assert first["created"] is True
    assert first["dream"]["dream_date"] == "2026-06-02"
    assert "阿嬷的信" in "\n".join(first["dream"]["triggers"])
    assert "<dream_context>" in first["dream"]["prompt_block"]
    assert second is not None
    assert second["created"] is False
    assert second["dream"]["dream_date"] == "2026-06-02"


def test_dream_engine_generates_low_intensity_dream_without_events(tmp_path: Path):
    engine = DreamEngine(tmp_path / "dreams.json", timezone_name="Asia/Shanghai")

    result = engine.ensure_due_dream(now_ms=_ms(2026, 6, 3, 3, 1))

    assert result is not None
    assert result["created"] is True
    assert result["dream"]["emotional_tone"] == "模糊"
    assert "没有明确事件" in result["dream"]["prompt_block"]


def test_dream_engine_records_truncated_interaction_seed(tmp_path: Path):
    engine = DreamEngine(tmp_path / "dreams.json", timezone_name="Asia/Shanghai")
    long_message = "今天的项目讨论很长，" + "细节" * 200

    seed = engine.record_interaction_seed("codex", long_message, now_ms=_ms(2026, 6, 2, 18))

    assert seed["kind"] == "user_interaction"
    assert seed["local_date"] == "2026-06-02"
    assert len(seed["summary"]) <= 140
    assert "今天的项目讨论很长" in seed["summary"]


def test_dream_engine_uses_llm_generator_when_available(tmp_path: Path):
    calls = []

    def fake_generator(payload: dict):
        calls.append(payload)
        return {
            "title": "旧照片里的雨",
            "emotional_tone": "温柔",
            "fragments": [
                "梦里有一张旧照片被雨水轻轻晕开，阿嬷的字迹没有消失。",
                "木生站在灯下，把昨天没说完的话折进信封。",
            ],
        }

    engine = DreamEngine(tmp_path / "dreams.json", timezone_name="Asia/Shanghai", llm_generator=fake_generator)
    engine.record_interaction_seed("hermes", "昨天聊到阿嬷的信和旧照片。", now_ms=_ms(2026, 6, 2, 21))

    result = engine.ensure_due_dream(now_ms=_ms(2026, 6, 3, 3, 1))

    assert result is not None
    assert calls
    assert calls[0]["dream_date"] == "2026-06-02"
    assert "阿嬷的信" in "\n".join(calls[0]["triggers"])
    assert result["dream"]["title"] == "旧照片里的雨"
    assert result["dream"]["emotional_tone"] == "温柔"
    assert "阿嬷的字迹没有消失" in result["dream"]["prompt_block"]


def test_dream_engine_falls_back_to_rules_when_llm_generator_fails(tmp_path: Path):
    def failing_generator(payload: dict):
        raise RuntimeError("deepseek unavailable")

    engine = DreamEngine(tmp_path / "dreams.json", timezone_name="Asia/Shanghai", llm_generator=failing_generator)
    engine.record_interaction_seed("hermes", "昨天一起聊了郑木生和阿嬷的信。", now_ms=_ms(2026, 6, 2, 21))

    result = engine.ensure_due_dream(now_ms=_ms(2026, 6, 3, 3, 1))

    assert result is not None
    assert result["dream"]["title"] == "没寄出的信"
    assert "梦里把" in result["dream"]["prompt_block"]
