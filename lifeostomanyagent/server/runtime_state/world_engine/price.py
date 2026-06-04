from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import replace
from typing import Any

from .models import PriceResult
from .prompts_world import WorldPrompts

PRICE_BASELINES: dict[str, tuple[int, tuple[int, int]]] = {
    "breakfast_home": (15, (8, 30)),
    "lunch_casual": (35, (20, 60)),
    "lunch_nice": (80, (50, 150)),
    "dinner_casual": (50, (30, 80)),
    "dinner_nice": (150, (80, 300)),
    "dinner_fancy": (400, (200, 800)),
    "cafe_drink": (35, (18, 58)),
    "bubble_tea": (18, (12, 30)),
    "dessert": (45, (25, 80)),
    "snack": (15, (5, 40)),
    "taxi_short": (15, (10, 25)),
    "taxi_cross_city": (50, (30, 80)),
    "bus": (2, (1, 5)),
    "metro": (4, (2, 8)),
    "hengqin_to_macau": (0, (0, 0)),
    "high_speed_nearby": (150, (50, 300)),
    "high_speed_far": (500, (200, 1200)),
    "flight_domestic": (800, (300, 2500)),
    "clothing_fast_fashion": (200, (80, 400)),
    "clothing_mid_range": (600, (300, 1200)),
    "clothing_designer": (2500, (1000, 8000)),
    "cosmetics_daily": (150, (50, 300)),
    "cosmetics_premium": (500, (200, 1500)),
    "book": (45, (25, 80)),
    "stationery": (30, (10, 80)),
    "grocery": (60, (30, 120)),
    "movie_ticket": (45, (30, 80)),
    "exhibition": (80, (0, 200)),
    "gym_monthly": (300, (150, 600)),
    "karaoke_per_person": (80, (40, 150)),
    "spa": (300, (150, 800)),
    "concert": (500, (200, 2000)),
    "groceries_daily": (60, (30, 120)),
    "utilities_monthly": (300, (150, 500)),
    "phone_monthly": (100, (50, 200)),
    "flowers_bouquet": (120, (50, 300)),
    "pet_food_monthly": (200, (100, 400)),
    "pet_vet_visit": (300, (100, 1000)),
    "haircut": (150, (50, 500)),
    "phone_mid": (4000, (2000, 6000)),
    "phone_flagship": (8000, (5000, 15000)),
    "laptop": (8000, (4000, 20000)),
    "car_economy": (100000, (70000, 150000)),
    "car_mid": (200000, (150000, 350000)),
    "car_luxury": (500000, (300000, 1000000)),
}


KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("早餐", "breakfast"), "breakfast_home"),
    (("午餐", "中饭", "lunch"), "lunch_casual"),
    (("晚餐", "dinner"), "dinner_casual"),
    (("咖啡", "coffee", "拿铁", "美式"), "cafe_drink"),
    (("奶茶", "bubble tea"), "bubble_tea"),
    (("甜品", "dessert", "蛋糕"), "dessert"),
    (("零食", "snack"), "snack"),
    (("出租", "打车", "taxi"), "taxi_short"),
    (("公交", "bus"), "bus"),
    (("地铁", "metro"), "metro"),
    (("高铁", "high speed"), "high_speed_nearby"),
    (("机票", "flight", "飞机"), "flight_domestic"),
    (("优衣库", "zara", "fast fashion"), "clothing_fast_fashion"),
    (("衣服", "衬衫", "外套", "clothing"), "clothing_mid_range"),
    (("化妆", "口红", "cosmetics"), "cosmetics_daily"),
    (("iphone", "手机", "phone"), "phone_flagship"),
    (("macbook", "laptop", "电脑"), "laptop"),
    (("特斯拉", "tesla", "model", "汽车", "车"), "car_mid"),
    (("书", "book"), "book"),
    (("电影", "movie"), "movie_ticket"),
    (("展览", "exhibition"), "exhibition"),
    (("健身", "gym"), "gym_monthly"),
    (("ktv", "karaoke"), "karaoke_per_person"),
    (("spa", "按摩"), "spa"),
    (("演唱会", "concert"), "concert"),
    (("花", "flowers"), "flowers_bouquet"),
    (("理发", "haircut"), "haircut"),
    (("猫粮", "狗粮", "pet food"), "pet_food_monthly"),
    (("兽医", "vet"), "pet_vet_visit"),
    (("超市", "grocery", "买菜"), "grocery"),
]


CATEGORY_FALLBACKS = {
    "food": "lunch_casual",
    "clothing": "clothing_mid_range",
    "vehicle": "car_mid",
    "digital": "phone_mid",
    "home_item": "groceries_daily",
    "pet": "pet_food_monthly",
    "entertainment": "movie_ticket",
    "cosmetics": "cosmetics_daily",
    "travel": "taxi_short",
    "subscription": "phone_monthly",
}


class PriceOracle:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self._cache: dict[tuple[str, str | None, str | None], PriceResult] = {}

    def query(
        self,
        item: str,
        category: str | None = None,
        location: str | None = None,
    ) -> PriceResult:
        cache_key = (item.lower(), category, location)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._keyword_price(item, category)
        if self.use_llm and result.confidence < 0.6:
            result = self._query_deepseek(item, category, location) or result

        self._cache[cache_key] = result
        return result

    def _keyword_price(self, item: str, category: str | None) -> PriceResult:
        lowered = item.lower()
        for keywords, key in KEYWORDS:
            if any(keyword.lower() in lowered for keyword in keywords):
                estimated, price_range = PRICE_BASELINES[key]
                return PriceResult(
                    item=item,
                    estimated_price=estimated,
                    price_range=price_range,
                    confidence=0.85,
                    source="keyword",
                    matched_key=key,
                )

        fallback_key = CATEGORY_FALLBACKS.get(category or "")
        if fallback_key:
            estimated, price_range = PRICE_BASELINES[fallback_key]
            return PriceResult(
                item=item,
                estimated_price=estimated,
                price_range=price_range,
                confidence=0.65,
                source="category_fallback",
                matched_key=fallback_key,
            )

        return PriceResult(
            item=item,
            estimated_price=100,
            price_range=(30, 300),
            confidence=0.3,
            source="default",
            matched_key=None,
        )

    def _query_deepseek(
        self,
        item: str,
        category: str | None,
        location: str | None,
    ) -> PriceResult | None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return None

        prompt = WorldPrompts.price_estimate_prompt(item, category, location)
        body = json.dumps(
            {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return replace(
                self._keyword_price(item, category),
                estimated_price=int(parsed["estimated_price"]),
                price_range=(int(parsed["low"]), int(parsed["high"])),
                confidence=float(parsed.get("confidence", 0.7)),
                source="deepseek",
                matched_key=None,
            )
        except Exception:
            return None
