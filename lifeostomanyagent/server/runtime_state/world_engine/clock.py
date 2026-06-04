from __future__ import annotations

import json
import sqlite3
from typing import Any

from sqlalchemy import delete, select

from lifeostomanyagent.server.db.models import WorldClockEventRow

from .models import current_millis
from .store import SQLWorldStore, WorldStore


def _loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "type": row["type"],
        "subject": row["subject"],
        "triggerAt": row["trigger_at"],
        "factId": row["fact_id"],
        "onTrigger": row["on_trigger"],
        "payload": _loads(row["payload_json"]),
        "fired": bool(row["fired"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


class WorldClock:
    def __init__(self, store: WorldStore):
        self.store = store
        self.conn = store.conn
        self.ensure_tables()

    def ensure_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS world_pending_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                subject TEXT NOT NULL,
                trigger_at INTEGER NOT NULL,
                fact_id INTEGER,
                on_trigger TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                fired INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

    def schedule_pending_event(
        self,
        event_type: str,
        subject: str,
        trigger_at: int,
        fact_id: int | None,
        on_trigger: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = current_millis()
        cursor = self.conn.execute(
            """
            INSERT INTO world_pending_events (
                type, subject, trigger_at, fact_id, on_trigger, payload_json,
                fired, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                event_type,
                subject,
                trigger_at,
                fact_id,
                on_trigger,
                json.dumps(payload or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        self.conn.commit()
        return self.get_event(cursor.lastrowid)

    def get_event(self, event_id: int) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM world_pending_events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"pending event not found: {event_id}")
        return _row_to_event(row)

    def get_upcoming_events(self, now: int, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM world_pending_events
            WHERE fired = 0 AND trigger_at > ?
            ORDER BY trigger_at ASC, id ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def get_overdue_events(self, now: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM world_pending_events
            WHERE fired = 0 AND trigger_at <= ?
            ORDER BY trigger_at ASC, id ASC
            """,
            (now,),
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def get_pending_events_by_fact(self, fact_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM world_pending_events WHERE fact_id = ? ORDER BY id",
            (fact_id,),
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def fire_overdue_events(self, now: int) -> list[dict[str, Any]]:
        fired: list[dict[str, Any]] = []
        for event in self.get_overdue_events(now):
            if event["onTrigger"] == "activate_fact" and event["factId"]:
                fact = self.store.get_fact(event["factId"])
                if fact["status"] == "pending":
                    self.store.update_fact_status(event["factId"], "active")
                    self.store.add_fact_event(
                        event["factId"],
                        event["type"],
                        event["subject"],
                        created_at=now,
                        metadata=event["payload"],
                    )
            self.conn.execute(
                "UPDATE world_pending_events SET fired = 1, updated_at = ? WHERE id = ?",
                (current_millis(), event["id"]),
            )
            self.conn.commit()
            fired.append(self.get_event(event["id"]))
        return fired

    def cancel_pending_event(self, event_id: int) -> None:
        self.conn.execute("DELETE FROM world_pending_events WHERE id = ?", (event_id,))
        self.conn.commit()


def _row_to_sql_event(row: WorldClockEventRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "type": row.type,
        "subject": row.subject,
        "triggerAt": row.trigger_at,
        "factId": row.fact_id,
        "onTrigger": row.on_trigger,
        "payload": dict(row.payload_json or {}),
        "fired": bool(row.fired),
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
    }


class SQLWorldClock:
    def __init__(self, store: SQLWorldStore):
        self.store = store
        self.db = store.db
        self.world_id = store.world_id

    def schedule_pending_event(
        self,
        event_type: str,
        subject: str,
        trigger_at: int,
        fact_id: int | None,
        on_trigger: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = current_millis()
        row = WorldClockEventRow(
            world_id=self.world_id,
            type=event_type,
            subject=subject,
            trigger_at=trigger_at,
            fact_id=fact_id,
            on_trigger=on_trigger,
            payload_json=payload or {},
            fired=False,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _row_to_sql_event(row)

    def get_event(self, event_id: int) -> dict[str, Any]:
        row = self.db.scalar(
            select(WorldClockEventRow).where(
                WorldClockEventRow.world_id == self.world_id,
                WorldClockEventRow.id == event_id,
            )
        )
        if row is None:
            raise KeyError(f"pending event not found: {event_id}")
        return _row_to_sql_event(row)

    def get_upcoming_events(self, now: int, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(WorldClockEventRow)
            .where(
                WorldClockEventRow.world_id == self.world_id,
                WorldClockEventRow.fired.is_(False),
                WorldClockEventRow.trigger_at > now,
            )
            .order_by(WorldClockEventRow.trigger_at.asc(), WorldClockEventRow.id.asc())
            .limit(limit)
        ).all()
        return [_row_to_sql_event(row) for row in rows]

    def get_overdue_events(self, now: int) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(WorldClockEventRow)
            .where(
                WorldClockEventRow.world_id == self.world_id,
                WorldClockEventRow.fired.is_(False),
                WorldClockEventRow.trigger_at <= now,
            )
            .order_by(WorldClockEventRow.trigger_at.asc(), WorldClockEventRow.id.asc())
        ).all()
        return [_row_to_sql_event(row) for row in rows]

    def get_pending_events_by_fact(self, fact_id: int) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(WorldClockEventRow)
            .where(
                WorldClockEventRow.world_id == self.world_id, WorldClockEventRow.fact_id == fact_id
            )
            .order_by(WorldClockEventRow.id.asc())
        ).all()
        return [_row_to_sql_event(row) for row in rows]

    def fire_overdue_events(self, now: int) -> list[dict[str, Any]]:
        fired: list[dict[str, Any]] = []
        for event in self.get_overdue_events(now):
            if event["onTrigger"] == "activate_fact" and event["factId"]:
                fact = self.store.get_fact(event["factId"])
                if fact["status"] == "pending":
                    self.store.update_fact_status(event["factId"], "active")
                    self.store.add_fact_event(
                        event["factId"],
                        event["type"],
                        event["subject"],
                        created_at=now,
                        metadata=event["payload"],
                    )
            row = self.db.scalar(
                select(WorldClockEventRow).where(
                    WorldClockEventRow.world_id == self.world_id,
                    WorldClockEventRow.id == event["id"],
                )
            )
            if row:
                row.fired = True
                row.updated_at = current_millis()
                self.db.commit()
                self.db.refresh(row)
                fired.append(_row_to_sql_event(row))
        return fired

    def cancel_pending_event(self, event_id: int) -> None:
        self.db.execute(
            delete(WorldClockEventRow).where(
                WorldClockEventRow.world_id == self.world_id,
                WorldClockEventRow.id == event_id,
            )
        )
        self.db.commit()
