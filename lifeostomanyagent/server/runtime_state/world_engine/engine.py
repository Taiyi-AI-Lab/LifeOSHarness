from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .clock import WorldClock
from .enrich import FactEnricher
from .fact_extractor import AliceFactExtractor
from .models import DAY_MS, current_millis
from .price import PriceOracle
from .rules import days_to_millis, validate_action
from .store import WorldStore
from .venues import VenueRegistry

WORLD_DEBUG_ACTION_SPECS = (
    {
        "action": "getActiveFacts",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {},
        "result": "active world_facts rows",
    },
    {
        "action": "getPendingFacts",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {},
        "result": "pending delivery world_facts rows",
    },
    {
        "action": "getAllFacts",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {},
        "result": "all world_facts rows",
    },
    {
        "action": "getUpcomingEvents",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"days": 7},
        "result": "upcoming scheduled world events",
    },
    {
        "action": "getVisitHistory",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"limit": 20},
        "result": "venue visit rows",
    },
    {
        "action": "getFavoriteVenues",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"limit": 10},
        "result": "aggregated favorite venues",
    },
    {
        "action": "getWorldPrompt",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {},
        "result": "world facts prompt block",
    },
    {
        "action": "purchase",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"item": "咖啡", "category": "food", "balance": 500},
        "result": "purchase validation and created fact",
    },
    {
        "action": "queryPrice",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"item": "咖啡", "category": "food", "location": "横琴"},
        "result": "estimated price range",
    },
    {
        "action": "extractFacts",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"messages": [{"role": "assistant", "content": "我买了一台相机"}]},
        "result": "extracted and committed facts",
    },
    {
        "action": "retireFact",
        "preloadMethod": "worldRetireFact",
        "ipc": "world:debug",
        "paramsExample": {"id": 1, "reason": "损坏"},
        "result": "gone fact and status_change event",
    },
    {
        "action": "deleteFact",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"id": 1},
        "result": "delete success flag",
    },
    {
        "action": "enrichFact",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"factId": 1},
        "result": "metadata/image enrichment result",
    },
    {
        "action": "addFact",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"category": "home_item", "subject": "台灯", "description": "书桌上使用"},
        "result": "created world fact",
    },
    {
        "action": "addFactEvent",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"factId": 1, "type": "note", "content": "清洁过一次"},
        "result": "created fact event",
    },
    {
        "action": "getFactEvents",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"factId": 1, "limit": 50},
        "result": "events for a fact",
    },
    {
        "action": "getRecentEvents",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {"limit": 20},
        "result": "recent fact events",
    },
    {
        "action": "worldTick",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {},
        "result": "delivered facts and fired events",
    },
    {
        "action": "initWorldEngine",
        "preloadMethod": "worldDebug",
        "ipc": "world:debug",
        "paramsExample": {},
        "result": "startup cleanup and delivered/fired counts",
    },
)

WORLD_DEBUG_ACTIONS = tuple(spec["action"] for spec in WORLD_DEBUG_ACTION_SPECS)


def get_world_debug_action_specs() -> list[dict[str, Any]]:
    return [{**spec, "paramsExample": dict(spec["paramsExample"])} for spec in WORLD_DEBUG_ACTION_SPECS]


class WorldEngine:
    def __init__(self, db_path: str = "lifeos/world.sqlite3", *, use_llm: bool = False):
        self.store = WorldStore(db_path)
        self.clock = WorldClock(self.store)
        self.venues = VenueRegistry(self.store)
        self.price_oracle = PriceOracle(use_llm=use_llm)

    def init_world_engine(self, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else current_millis()
        delivered = self.store.process_deliveries(now)
        fired = self.clock.fire_overdue_events(now)
        dirty = self.store.clean_dirty_facts_once()
        duplicates = self.store.deduplicate_wardrobe_facts()
        vague = self.store.clean_vague_recovery_facts()
        return {
            "delivered": delivered,
            "firedEvents": fired,
            "cleanup": {
                "dirtyFacts": dirty,
                "duplicateWardrobeFacts": duplicates,
                "vagueRecoveryFacts": vague,
            },
        }

    def world_tick(self, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else current_millis()
        delivered = self.store.process_deliveries(now)
        fired = self.clock.fire_overdue_events(now)
        return {"delivered": delivered, "firedEvents": fired}

    def world_get_belongings(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "active": self.store.get_active_facts(),
            "pending": self.store.get_pending_facts(),
            "gone": self.store.get_gone_facts(),
        }

    def world_debug(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        *,
        balance: int = 0,
        now: int | None = None,
    ) -> dict[str, Any]:
        params = params or {}
        now = now if now is not None else current_millis()

        try:
            if action == "getActiveFacts":
                return {"ok": True, "data": self.store.get_active_facts()}
            if action == "getPendingFacts":
                return {"ok": True, "data": self.store.get_pending_facts()}
            if action == "getAllFacts":
                return {"ok": True, "data": self.store.get_all_facts()}
            if action == "getUpcomingEvents":
                return {"ok": True, "data": self.clock.get_upcoming_events(now)}
            if action == "getVisitHistory":
                return {"ok": True, "data": self.venues.get_visit_history(limit=params.get("limit", 20))}
            if action == "getFavoriteVenues":
                return {"ok": True, "data": self.venues.get_favorite_venues(limit=params.get("limit", 10))}
            if action == "getWorldPrompt":
                return {"ok": True, "data": self.build_world_facts_prompt_block(now=now)}
            if action == "purchase":
                return {
                    "ok": True,
                    "data": self.purchase(params, balance=int(params.get("balance", balance)), now=now),
                }
            if action == "queryPrice":
                price = self.price_oracle.query(params.get("item", ""), params.get("category"), params.get("location"))
                return {
                    "ok": True,
                    "data": {
                        "estimatedPrice": price.estimated_price,
                        "priceRange": list(price.price_range),
                        "source": price.source,
                        "confidence": price.confidence,
                    },
                }
            if action == "extractFacts":
                extractor = AliceFactExtractor(self.store)
                llm = params.get("llm")
                if not callable(llm):
                    return {"ok": False, "error": "extractFacts requires params.llm callable in the Python replica"}
                extracted = extractor.extract_alice_facts(params.get("messages", []), llm)
                committed = extractor.commit_extracted_facts(extracted) if extracted else 0
                return {"ok": True, "data": {"extracted": extracted, "committed": committed}}
            if action == "retireFact":
                fact = self.store.retire_fact(int(params.get("id")), params.get("reason") or "未知原因", now=now)
                if fact is None:
                    return {"ok": False, "error": "事实不存在"}
                self.store.add_fact_event(
                    fact["id"],
                    "status_change",
                    f"退役：{params.get('reason') or '未知原因'}",
                    created_at=now,
                    metadata={"source": "debug:gm"},
                )
                return {"ok": True, "data": fact}
            if action == "deleteFact":
                deleted = self.store.delete_fact(int(params.get("id")))
                return {"ok": deleted, "error": None if deleted else "事实不存在"}
            if action == "enrichFact":
                fact_id = int(params.get("factId") or params.get("id"))
                output_dir = params.get("outputDir") or str(Path(self.store.db_path).parent / "fact-images")
                result = FactEnricher(self.store, output_dir=output_dir, llm=params.get("llm")).enrich_fact(fact_id, now=now)
                return {"ok": "error" not in result, "data": result, "error": result.get("error")}
            if action == "addFact":
                fact = self.store.add_fact(
                    category=params.get("category") or "possession",
                    subject=params.get("subject") or "",
                    description=params.get("description") or "",
                    status=params.get("status") or "active",
                    condition=params.get("condition") or "正常",
                    acquired_at=params.get("acquiredAt") or now,
                    acquired_via=params.get("acquiredVia") or "debug:manual",
                    related_moment_id=params.get("relatedMomentId"),
                    real_world_price=params.get("realWorldPrice"),
                    paid_price=params.get("paidPrice"),
                    delivery_at=params.get("deliveryAt"),
                    expires_at=params.get("expiresAt"),
                    metadata=params.get("metadata") or {},
                )
                return {"ok": True, "data": fact}
            if action == "addFactEvent":
                event = self.store.add_fact_event(
                    params.get("factId"),
                    params.get("type") or "note",
                    params.get("content") or "",
                    created_at=now,
                    metadata={
                        "createdVia": params.get("createdVia") or "debug:manual",
                        "updateCondition": params.get("updateCondition"),
                    },
                )
                return {"ok": True, "data": event}
            if action == "getFactEvents":
                return {
                    "ok": True,
                    "data": self.store.get_fact_events(int(params.get("factId")), int(params.get("limit", 50))),
                }
            if action == "getRecentEvents":
                return {"ok": True, "data": self.store.get_recent_events(limit=int(params.get("limit", 20)))}
            if action == "worldTick":
                return {"ok": True, "data": self.world_tick(now=now)}
            if action == "initWorldEngine":
                return {"ok": True, "data": self.init_world_engine(now=now)}
            return {"ok": False, "error": f"Unknown action: {action}"}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def purchase(
        self,
        purchase_input: dict[str, Any],
        *,
        balance: int,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = now if now is not None else current_millis()
        item = purchase_input["item"]
        category = purchase_input.get("category", "general")
        location = purchase_input.get("location")
        price = self.price_oracle.query(item, category, location)
        requested_amount = int(purchase_input.get("price") or price.estimated_price)
        warnings: list[str] = []

        if category == "clothing":
            warnings.append("衣物类购买建议同时写入 wardrobeCategory 元数据，便于衣柜去重")

        validation = validate_action(
            {
                "type": "purchase",
                "item": item,
                "category": category,
                "amount": requested_amount,
                "location": location,
            },
            {
                "balance": balance,
                "time": now,
                "location": location,
                "facts": self.store.get_active_facts(),
                "priceOracle": self.price_oracle,
            },
        )

        warnings.extend(validation.warnings)
        if not validation.ok:
            return {
                "success": False,
                "finalPrice": requested_amount,
                "violation": validation.violation,
                "warnings": warnings,
            }

        final_price = int(validation.estimated_price or requested_amount)
        delivery_days = validation.delivery_days
        delivery_at = now + days_to_millis(delivery_days) if delivery_days > 0 else None
        status = "pending" if delivery_at else "active"

        fact = self.store.add_fact(
            category=category,
            subject=item,
            description=f"通过购买获得：{item}",
            status=status,
            condition="正常",
            acquired_at=now,
            acquired_via="purchase",
            related_moment_id=purchase_input.get("relatedMomentId"),
            real_world_price=price.estimated_price,
            paid_price=final_price,
            delivery_at=delivery_at,
            metadata={
                "priceSource": price.source,
                "priceConfidence": price.confidence,
                "deliveryDays": delivery_days,
                **purchase_input.get("metadata", {}),
            },
        )

        pending_event = None
        if delivery_at:
            pending_event = self.clock.schedule_pending_event(
                "delivery",
                f"{item} 交付",
                delivery_at,
                fact["id"],
                "activate_fact",
                {"item": item, "price": final_price},
            )

        return {
            "success": True,
            "fact": fact,
            "pendingEvent": pending_event,
            "finalPrice": final_price,
            "warnings": warnings,
        }

    def validate_and_enrich_day_script(
        self,
        activities: list[dict[str, Any]],
        *,
        balance: int,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = now if now is not None else current_millis()
        active_facts = self.store.get_active_facts()
        result: dict[str, list[Any]] = {
            "factInjections": [],
            "priceCorrections": [],
            "warnings": [],
        }

        self._inject_fact_hints(result, active_facts)
        self._inject_pending_delivery_hints(result, now)

        total_cost = 0
        for activity in activities:
            title = activity.get("title") or activity.get("name") or activity.get("description") or ""
            if not title:
                continue
            if "estimatedCost" not in activity and "cost" not in activity:
                continue
            raw_cost = int(activity.get("estimatedCost", activity.get("cost", 0)) or 0)
            price = self.price_oracle.query(title, activity.get("category"), activity.get("location"))
            total_cost += price.estimated_price
            if raw_cost == 0 or abs(raw_cost - price.estimated_price) / max(price.estimated_price, 1) > 0.5:
                result["priceCorrections"].append(
                    {
                        "activity": title,
                        "originalPrice": raw_cost,
                        "correctedPrice": price.estimated_price,
                        "priceRange": list(price.price_range),
                        "source": price.source,
                    }
                )

        if balance > 0 and total_cost > balance * 0.3:
            result["warnings"].append(f"当日预计消费 {total_cost} 元，超过余额的 30%")

        return result

    def build_world_facts_prompt_block(self, now: int | None = None) -> str:
        now = now if now is not None else current_millis()
        active_facts = self.store.get_active_facts()
        pending_facts = self.store.get_pending_facts()
        recent_events = self.store.get_recent_events(limit=5)
        favorite_venues = self.venues.get_favorite_venues(limit=5)
        lines = ["# World Facts"]

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        wardrobe: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for fact in active_facts:
            grouped[fact["category"]].append(fact)
            wardrobe_category = fact["metadata"].get("wardrobeCategory")
            if wardrobe_category:
                wardrobe[wardrobe_category].append(fact)

        for category, facts in sorted(grouped.items()):
            lines.append(f"\n## {category}")
            for fact in facts:
                age = _format_age(now - int(fact["acquiredAt"] or now))
                lines.append(f"- {fact['subject']}：{fact['description']}（{age}前获得）")

        if wardrobe:
            lines.append("\n## wardrobe")
            for category, facts in sorted(wardrobe.items()):
                names = "、".join(fact["subject"] for fact in facts)
                lines.append(f"- {category}: {names}")

        if pending_facts:
            lines.append("\n## pending")
            for fact in pending_facts:
                remaining = _format_age(max(0, int(fact["deliveryAt"] or now) - now))
                lines.append(f"- {fact['subject']}：预计 {remaining} 后交付")

        if recent_events:
            lines.append("\n## recent events")
            for event in recent_events:
                lines.append(f"- {event['subject']}")

        if favorite_venues:
            lines.append("\n## favorite venues")
            for venue in favorite_venues:
                lines.append(
                    f"- {venue['venueName']}：访问 {venue['metadata']['visitCount']} 次"
                )

        return "\n".join(lines)

    def _inject_fact_hints(
        self, result: dict[str, list[Any]], active_facts: list[dict[str, Any]]
    ) -> None:
        if any(fact["category"] == "pet" for fact in active_facts):
            result["factInjections"].append("已有宠物事实：日程中应考虑喂食、陪伴或照料宠物。")
        if any(fact["category"] == "vehicle" for fact in active_facts):
            result["factInjections"].append("已有车辆事实：远距离出行可优先考虑开车。")
        if any(fact["category"] == "subscription" for fact in active_facts):
            result["factInjections"].append("已有订阅事实：安排活动时可复用订阅权益。")

    def _inject_pending_delivery_hints(self, result: dict[str, list[Any]], now: int) -> None:
        for fact in self.store.get_pending_facts():
            delivery_at = fact["deliveryAt"]
            if not delivery_at:
                continue
            days = max(0, int((delivery_at - now + DAY_MS - 1) // DAY_MS))
            if days in {1, 2, 3}:
                result["factInjections"].append(f"{fact['subject']} 即将送达，预计 {days} 天内交付。")


def _format_age(delta_ms: int) -> str:
    minutes = delta_ms // 60_000
    if minutes < 60:
        return f"{max(1, minutes)} 分钟"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} 小时"
    days = hours // 24
    if days < 30:
        return f"{days} 天"
    return f"{days // 30} 个月"
