from __future__ import annotations

import argparse
import json

from .engine import WorldEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Alice World Engine Python 复现 demo")
    parser.add_argument("--db", default="lifeos/world.sqlite3", help="SQLite 数据库路径")
    subparsers = parser.add_subparsers(dest="command", required=True)

    buy = subparsers.add_parser("purchase", help="模拟一次购买")
    buy.add_argument("item")
    buy.add_argument("--category", default="general")
    buy.add_argument("--price", type=int)
    buy.add_argument("--balance", type=int, default=10_000)
    buy.add_argument("--location", default="珠海")

    subparsers.add_parser("tick", help="触发到期世界事件")
    subparsers.add_parser("prompt", help="输出 World Facts prompt block")

    args = parser.parse_args()
    engine = WorldEngine(args.db)

    if args.command == "purchase":
        result = engine.purchase(
            {
                "item": args.item,
                "category": args.category,
                "price": args.price,
                "location": args.location,
            },
            balance=args.balance,
        )
    elif args.command == "tick":
        result = engine.world_tick()
    else:
        print(engine.build_world_facts_prompt_block())
        return

    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))


def _jsonable(value):
    if isinstance(value, Exception):
        return str(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    main()
