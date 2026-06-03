from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import DAY_MS, ValidationResult, ValidationViolation


DELIVERY_RANGES = {
    "vehicle": (3, 30),
    "digital": (1, 3),
    "home_item": (1, 7),
}


def validate_action(action: dict[str, Any], context: dict[str, Any]) -> ValidationResult:
    current = deepcopy(action)
    warnings: list[str] = []
    estimated_price: int | None = None
    delivery_days = 0
    price_result = None

    if current.get("type") == "purchase":
        price_oracle = context["priceOracle"]
        price_result = price_oracle.query(
            current.get("item", ""),
            current.get("category"),
            current.get("location"),
        )
        estimated_price = price_result.estimated_price
        amount = int(current.get("amount") or estimated_price)
        low, high = price_result.price_range

        if amount > 0 and amount < low * 0.5:
            return ValidationResult(
                ok=False,
                violation=ValidationViolation(
                    code="price_too_low",
                    message=f"{current.get('item')} 的价格 {amount} 明显低于现实区间 {low}-{high}",
                    rule_id="price_reality",
                    details=price_result.to_dict(),
                ),
            )
        if amount < low or amount > high * 1.5:
            current["amount"] = estimated_price
        else:
            current["amount"] = amount

        balance = int(context.get("balance") or 0)
        if current["amount"] > balance:
            return ValidationResult(
                ok=False,
                violation=ValidationViolation(
                    code="insufficient_funds",
                    message=f"余额 {balance} 不足以支付 {current['amount']}",
                    rule_id="budget_check",
                    details={"balance": balance, "amount": current["amount"]},
                ),
                estimated_price=current["amount"],
                price_result=price_result,
            )
        if balance > 0 and current["amount"] > balance * 0.5:
            warnings.append("本次消费超过余额的一半")

        category = current.get("category")
        if category in DELIVERY_RANGES:
            start, _end = DELIVERY_RANGES[category]
            delivery_days = start

    if current.get("type") == "enter_venue":
        open_time = current.get("venue", {}).get("open_time")
        if open_time and not _is_open(open_time, context.get("time")):
            return ValidationResult(
                ok=False,
                violation=ValidationViolation(
                    code="venue_closed",
                    message="场所当前不在营业时间内",
                    rule_id="operating_hours",
                    details={"openTime": open_time},
                ),
            )

    if current.get("type") == "travel":
        distance = float(current.get("distanceKm") or 0)
        vehicle = next(
            (
                fact
                for fact in context.get("facts", [])
                if fact.get("category") == "vehicle" and fact.get("status") == "active"
            ),
            None,
        )
        if vehicle and distance > 3:
            current["travelMode"] = "drive"
            current["travelNote"] = f"使用已有车辆 {vehicle['subject']} 出行"

    return ValidationResult(
        ok=True,
        action=current,
        warnings=warnings,
        estimated_price=current.get("amount", estimated_price),
        delivery_days=delivery_days,
        price_result=price_result,
    )


def _is_open(open_time: str, now: int | None) -> bool:
    if now is None:
        return True
    try:
        import datetime as dt

        start_text, end_text = [part.strip() for part in open_time.split("-", 1)]
        start_hour, start_minute = [int(part) for part in start_text.split(":", 1)]
        end_hour, end_minute = [int(part) for part in end_text.split(":", 1)]
        local = dt.datetime.fromtimestamp(now / 1000)
        current_minutes = local.hour * 60 + local.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        if end_minutes < start_minutes:
            return current_minutes >= start_minutes or current_minutes <= end_minutes
        return start_minutes <= current_minutes <= end_minutes
    except Exception:
        return True


def days_to_millis(days: int) -> int:
    return days * DAY_MS
