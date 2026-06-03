from __future__ import annotations

from typing import Any


HOUR_MS = 3_600_000
DAY_MS = 86_400_000
WAKE_RESET_MS = 43_200_000


class EmotionRules:
    @staticmethod
    def tick_physiological(state: dict[str, Any], *, hour: int, now: int) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        status_tags = list(state.get("statusTags", []))
        energy = int(state.get("energy", 0))

        if hour >= 23 or hour < 6:
            updates["energy"] = energy - 8
            if "困了" not in status_tags:
                status_tags.append("困了")
        if 6 <= hour <= 8:
            if energy < 70:
                updates["energy"] = 80
            status_tags = [tag for tag in status_tags if tag not in ("困了", "有点累")]
            if not state.get("wokeUpAt") or now - int(state.get("wokeUpAt") or 0) > WAKE_RESET_MS:
                updates["wokeUpAt"] = now
        if (9 <= hour < 12) or (14 <= hour < 23):
            if energy < 70:
                updates["energy"] = energy + 3
        if 12 <= hour < 14:
            updates["energy"] = energy - 5

        next_energy = updates.get("energy", energy)
        if next_energy < 30 and "有点累" not in status_tags:
            status_tags.append("有点累")
        if next_energy >= 30:
            status_tags = [tag for tag in status_tags if tag != "有点累"]

        mood = int(state.get("mood", 0))
        if mood > 62:
            updates["mood"] = mood - 2
        elif mood < 58:
            updates["mood"] = mood + 2

        last_chat_at = state.get("lastChatAt")
        if last_chat_at and (now - int(last_chat_at)) / HOUR_MS >= 12:
            updates["socialNeed"] = min(100, int(state.get("socialNeed", 0)) + 3)

        updates["statusTags"] = status_tags
        return updates

    @staticmethod
    def on_chat_started(state: dict[str, Any], *, now: int) -> dict[str, Any]:
        return {"lastChatAt": now, "socialNeed": max(0, int(state.get("socialNeed", 0)) - 20)}

    @staticmethod
    def on_chat_ended(state: dict[str, Any], *, meaningful: bool) -> dict[str, Any]:
        if meaningful:
            return {
                "mood": int(state.get("mood", 0)) + 10,
                "trust": int(state.get("trust", 0)) + 2,
                "familiarity": int(state.get("familiarity", 0)) + 1,
            }
        return {"familiarity": int(state.get("familiarity", 0)) + 1}

    @staticmethod
    def on_income_received(state: dict[str, Any]) -> dict[str, Any]:
        return {"mood": int(state.get("mood", 0)) + 15, "affinity": int(state.get("affinity", 0)) + 5}

    @staticmethod
    def on_moment_liked(state: dict[str, Any]) -> dict[str, Any]:
        return {"mood": int(state.get("mood", 0)) + 5, "affinity": int(state.get("affinity", 0)) + 2}

    @staticmethod
    def on_moment_commented(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "mood": int(state.get("mood", 0)) + 8,
            "affinity": int(state.get("affinity", 0)) + 3,
            "socialNeed": max(0, int(state.get("socialNeed", 0)) - 10),
        }

    @staticmethod
    def on_negative_interaction(state: dict[str, Any]) -> dict[str, Any]:
        return {"mood": int(state.get("mood", 0)) - 15, "affinity": int(state.get("affinity", 0)) - 8}

    @staticmethod
    def on_daily_inactivity_check(state: dict[str, Any], *, now: int) -> dict[str, Any] | None:
        last_chat_at = state.get("lastChatAt")
        if last_chat_at and (now - int(last_chat_at)) / DAY_MS >= 3:
            return {
                "affinity": int(state.get("affinity", 0)) - 3,
                "socialNeed": min(100, int(state.get("socialNeed", 0)) + 30),
            }
        return None

    @staticmethod
    def on_consecutive_use_days(state: dict[str, Any], days: int) -> dict[str, Any] | None:
        return {"trust": int(state.get("trust", 0)) + 5} if days >= 7 and days % 7 == 0 else None

    @staticmethod
    def on_day_script_executed(state: dict[str, Any], effects: dict[str, int | None]) -> dict[str, Any]:
        updates = {}
        if effects.get("moodEffect"):
            updates["mood"] = int(state.get("mood", 0)) + int(effects["moodEffect"] or 0)
        if effects.get("energyEffect"):
            updates["energy"] = int(state.get("energy", 0)) + int(effects["energyEffect"] or 0)
        if effects.get("socialNeedEffect"):
            updates["socialNeed"] = int(state.get("socialNeed", 0)) + int(effects["socialNeedEffect"] or 0)
        return updates

    @staticmethod
    def get_behavior_constraints(state: dict[str, Any]) -> dict[str, bool]:
        relationship_level = EmotionRules.relationship_level(state)
        blocked = "blocked" in state.get("statusTags", [])
        return {
            "canPostMoment": int(state.get("mood", 0)) >= 30 and not blocked,
            "canInitiateChat": int(state.get("socialNeed", 0)) > 80 and int(state.get("affinity", 0)) > 60 and relationship_level >= 3 and not blocked,
            "toneLowEnergy": int(state.get("energy", 0)) < 20,
            "toneDepressed": int(state.get("mood", 0)) < 30,
            "toneCheerful": int(state.get("mood", 0)) > 80 and not blocked,
            "toneDetached": int(state.get("affinity", 0)) < 30,
            "toneBlocked": blocked,
            "shouldSharePrivate": int(state.get("affinity", 0)) > 80 and not blocked,
        }

    @staticmethod
    def relationship_level(state: dict[str, Any]) -> int:
        affinity = int(state.get("affinity", 0))
        trust = int(state.get("trust", 0))
        if affinity >= 86 and trust >= 76:
            return 5
        if affinity >= 66 and trust >= 56:
            return 4
        if affinity >= 46 and trust >= 36:
            return 3
        if affinity >= 21 and trust >= 16:
            return 2
        return 1
