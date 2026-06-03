from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import current_millis


def _loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _row_to_fact(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "category": row["category"],
        "subject": row["subject"],
        "description": row["description"],
        "status": row["status"],
        "condition": row["condition"],
        "acquiredAt": row["acquired_at"],
        "acquiredVia": row["acquired_via"],
        "relatedMomentId": row["related_moment_id"],
        "realWorldPrice": row["real_world_price"],
        "paidPrice": row["paid_price"],
        "deliveryAt": row["delivery_at"],
        "expiresAt": row["expires_at"],
        "metadata": _loads(row["metadata_json"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


class WorldStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.ensure_world_tables()

    def ensure_world_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS world_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                condition TEXT NOT NULL DEFAULT '正常',
                acquired_at INTEGER,
                acquired_via TEXT,
                related_moment_id TEXT,
                real_world_price INTEGER,
                paid_price INTEGER,
                delivery_at INTEGER,
                expires_at INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fact_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id INTEGER,
                event_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def add_fact(
        self,
        *,
        category: str,
        subject: str,
        description: str = "",
        status: str = "active",
        condition: str = "正常",
        acquired_at: int | None = None,
        acquired_via: str | None = None,
        related_moment_id: str | None = None,
        real_world_price: int | None = None,
        paid_price: int | None = None,
        delivery_at: int | None = None,
        expires_at: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = current_millis()
        acquired_at = acquired_at if acquired_at is not None else now
        cursor = self.conn.execute(
            """
            INSERT INTO world_facts (
                category, subject, description, status, condition, acquired_at,
                acquired_via, related_moment_id, real_world_price, paid_price,
                delivery_at, expires_at, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                subject,
                description,
                status,
                condition,
                acquired_at,
                acquired_via,
                related_moment_id,
                real_world_price,
                paid_price,
                delivery_at,
                expires_at,
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        self.conn.commit()
        return self.get_fact(cursor.lastrowid)

    def get_fact(self, fact_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM world_facts WHERE id = ?", (fact_id,)).fetchone()
        if row is None:
            raise KeyError(f"fact not found: {fact_id}")
        return _row_to_fact(row)

    def get_all_facts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM world_facts ORDER BY id").fetchall()
        return [_row_to_fact(row) for row in rows]

    def get_active_facts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM world_facts WHERE status = 'active' ORDER BY id"
        ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def get_pending_facts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM world_facts WHERE status = 'pending' ORDER BY delivery_at, id"
        ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def get_gone_facts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM world_facts WHERE status = 'gone' ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def get_facts_by_category(self, category: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM world_facts WHERE category = ? ORDER BY id", (category,)
        ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def update_fact_status(self, fact_id: int, status: str) -> dict[str, Any]:
        self.conn.execute(
            "UPDATE world_facts SET status = ?, updated_at = ? WHERE id = ?",
            (status, current_millis(), fact_id),
        )
        self.conn.commit()
        return self.get_fact(fact_id)

    def delete_fact(self, fact_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM world_facts WHERE id = ?", (fact_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def retire_fact(self, fact_id: int, reason: str, *, now: int | None = None) -> dict[str, Any] | None:
        try:
            fact = self.get_fact(fact_id)
        except KeyError:
            return None
        now = now if now is not None else current_millis()
        metadata = {
            **(fact.get("metadata") or {}),
            "retiredReason": reason,
            "retiredAt": now,
        }
        self.conn.execute(
            """
            UPDATE world_facts
            SET status = 'gone', metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(metadata, ensure_ascii=False), now, fact_id),
        )
        self.conn.commit()
        return self.get_fact(fact_id)

    def add_fact_event(
        self,
        fact_id: int | None,
        event_type: str,
        subject: str,
        *,
        created_at: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = created_at if created_at is not None else current_millis()
        cursor = self.conn.execute(
            """
            INSERT INTO fact_events (fact_id, event_type, subject, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                event_type,
                subject,
                created_at,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return self.get_fact_event(cursor.lastrowid)

    def get_fact_event(self, event_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM fact_events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(f"event not found: {event_id}")
        return {
            "id": row["id"],
            "factId": row["fact_id"],
            "eventType": row["event_type"],
            "subject": row["subject"],
            "createdAt": row["created_at"],
            "metadata": _loads(row["metadata_json"]),
        }

    def get_fact_events(self, fact_id: int, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM fact_events
            WHERE fact_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (fact_id, limit),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "factId": row["fact_id"],
                "eventType": row["event_type"],
                "subject": row["subject"],
                "createdAt": row["created_at"],
                "metadata": _loads(row["metadata_json"]),
            }
            for row in rows
        ]

    def get_recent_events(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM fact_events ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "factId": row["fact_id"],
                "eventType": row["event_type"],
                "subject": row["subject"],
                "createdAt": row["created_at"],
                "metadata": _loads(row["metadata_json"]),
            }
            for row in rows
        ]

    def process_deliveries(self, now: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM world_facts
            WHERE status = 'pending' AND delivery_at IS NOT NULL AND delivery_at <= ?
            ORDER BY delivery_at, id
            """,
            (now,),
        ).fetchall()
        activated: list[dict[str, Any]] = []
        for row in rows:
            fact = _row_to_fact(row)
            self.update_fact_status(fact["id"], "active")
            self.add_fact_event(
                fact["id"],
                "delivery",
                f"{fact['subject']} 已交付",
                created_at=now,
            )
            activated.append(self.get_fact(fact["id"]))
        return activated

    def clean_dirty_facts_once(self) -> int:
        dirty_subjects = {"恢复的回忆", "未知记忆", "临时恢复"}
        count = 0
        for fact in self.get_all_facts():
            if fact["subject"] in dirty_subjects or fact["description"] in dirty_subjects:
                self.delete_fact(fact["id"])
                count += 1
        return count

    def deduplicate_wardrobe_facts(self) -> int:
        seen: set[tuple[str, str, str]] = set()
        removed = 0
        for fact in self.get_all_facts():
            wardrobe_category = fact["metadata"].get("wardrobeCategory")
            if fact["category"] != "clothing" or not wardrobe_category:
                continue
            key = (fact["category"], fact["subject"], wardrobe_category)
            if key in seen:
                self.delete_fact(fact["id"])
                removed += 1
            else:
                seen.add(key)
        return removed

    def clean_vague_recovery_facts(self) -> int:
        vague_categories = {"moments-recovery", "recovery", "memory-recovery"}
        removed = 0
        for fact in self.get_all_facts():
            if fact["category"] in vague_categories:
                self.delete_fact(fact["id"])
                removed += 1
        return removed
