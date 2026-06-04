from dataclasses import dataclass, field
from typing import Any

DAY_MS = 86_400_000


def current_millis() -> int:
    import time

    return int(time.time() * 1000)


@dataclass
class PriceResult:
    item: str
    estimated_price: int
    price_range: tuple[int, int]
    currency: str = "CNY"
    confidence: float = 0.8
    source: str = "keyword"
    matched_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item": self.item,
            "estimatedPrice": self.estimated_price,
            "priceRange": list(self.price_range),
            "currency": self.currency,
            "confidence": self.confidence,
            "source": self.source,
            "matchedKey": self.matched_key,
        }


@dataclass
class ValidationViolation(Exception):
    code: str
    message: str
    rule_id: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass
class ValidationResult:
    ok: bool
    action: dict[str, Any] | None = None
    violation: ValidationViolation | None = None
    warnings: list[str] = field(default_factory=list)
    estimated_price: int | None = None
    delivery_days: int = 0
    price_result: PriceResult | None = None
