from __future__ import annotations

import json
import sqlite3
from typing import Any

from sqlalchemy import func, select

from lifeostomanyagent.server.db.models import VenueVisitRow

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


def _row_to_visit(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "venueName": row["venue_name"],
        "visitedAt": row["visited_at"],
        "spent": row["spent"],
        "rating": row["rating"],
        "note": row["note"],
        "metadata": _loads(row["metadata_json"]),
    }


class VenueRegistry:
    def __init__(self, store: WorldStore):
        self.store = store
        self.conn = store.conn
        self.ensure_tables()

    def ensure_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS venue_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venue_name TEXT NOT NULL,
                visited_at INTEGER NOT NULL,
                spent INTEGER NOT NULL DEFAULT 0,
                rating INTEGER,
                note TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        self.conn.commit()

    def record_visit(
        self,
        venue_name: str,
        *,
        spent: int = 0,
        now: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        visited_at = now if now is not None else current_millis()
        cursor = self.conn.execute(
            """
            INSERT INTO venue_visits (venue_name, visited_at, spent, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                venue_name,
                visited_at,
                spent,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return self.get_visit(cursor.lastrowid)

    def get_visit(self, visit_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM venue_visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            raise KeyError(f"visit not found: {visit_id}")
        return _row_to_visit(row)

    def rate_venue(self, visit_id: int, rating: int, note: str | None = None) -> dict[str, Any]:
        self.conn.execute(
            "UPDATE venue_visits SET rating = ?, note = ? WHERE id = ?",
            (rating, note, visit_id),
        )
        self.conn.commit()
        return self.get_visit(visit_id)

    def get_visit_history(
        self, venue_name: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        if venue_name:
            rows = self.conn.execute(
                """
                SELECT * FROM venue_visits
                WHERE venue_name = ?
                ORDER BY visited_at DESC, id DESC LIMIT ?
                """,
                (venue_name, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM venue_visits ORDER BY visited_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_visit(row) for row in rows]

    def get_visit_count(self, venue_name: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS count FROM venue_visits WHERE venue_name = ?",
            (venue_name,),
        ).fetchone()
        return int(row["count"])

    def get_favorite_venues(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                venue_name,
                COUNT(*) AS visit_count,
                COALESCE(AVG(rating), 0) AS avg_rating,
                MAX(visited_at) AS last_visited,
                SUM(spent) AS total_spent
            FROM venue_visits
            GROUP BY venue_name
            ORDER BY visit_count DESC, avg_rating DESC, last_visited DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "venueName": row["venue_name"],
                "avgRating": row["avg_rating"],
                "lastVisited": row["last_visited"],
                "totalSpent": row["total_spent"],
                "metadata": {"visitCount": row["visit_count"]},
            }
            for row in rows
        ]

    def generate_experience_feedback(self, venue_name: str, items: list[str] | None = None) -> str:
        history = self.get_visit_history(venue_name, limit=5)
        count = self.get_visit_count(venue_name)
        item_text = "、".join(items or []) or "这次安排"
        if not history:
            return f"第一次去 {venue_name}，可以关注 {item_text} 的实际体验。"
        avg_spent = sum(visit["spent"] for visit in history) / len(history)
        return f"{venue_name} 已访问 {count} 次，最近平均花费约 {avg_spent:.0f} 元，适合安排 {item_text}。"


def _row_to_sql_visit(row: VenueVisitRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "venueName": row.venue_name,
        "visitedAt": row.visited_at,
        "spent": row.spent,
        "rating": row.rating,
        "note": row.note,
        "metadata": dict(row.metadata_json or {}),
    }


class SQLVenueRegistry:
    def __init__(self, store: SQLWorldStore):
        self.store = store
        self.db = store.db
        self.world_id = store.world_id

    def record_visit(
        self,
        venue_name: str,
        *,
        spent: int = 0,
        now: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = VenueVisitRow(
            world_id=self.world_id,
            venue_name=venue_name,
            visited_at=now if now is not None else current_millis(),
            spent=spent,
            metadata_json=metadata or {},
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _row_to_sql_visit(row)

    def get_visit(self, visit_id: int) -> dict[str, Any]:
        row = self.db.scalar(
            select(VenueVisitRow).where(
                VenueVisitRow.world_id == self.world_id,
                VenueVisitRow.id == visit_id,
            )
        )
        if row is None:
            raise KeyError(f"visit not found: {visit_id}")
        return _row_to_sql_visit(row)

    def rate_venue(self, visit_id: int, rating: int, note: str | None = None) -> dict[str, Any]:
        row = self.db.scalar(
            select(VenueVisitRow).where(
                VenueVisitRow.world_id == self.world_id,
                VenueVisitRow.id == visit_id,
            )
        )
        if row is None:
            raise KeyError(f"visit not found: {visit_id}")
        row.rating = rating
        row.note = note
        self.db.commit()
        self.db.refresh(row)
        return _row_to_sql_visit(row)

    def get_visit_history(
        self, venue_name: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        query = select(VenueVisitRow).where(VenueVisitRow.world_id == self.world_id)
        if venue_name:
            query = query.where(VenueVisitRow.venue_name == venue_name)
        rows = self.db.scalars(
            query.order_by(VenueVisitRow.visited_at.desc(), VenueVisitRow.id.desc()).limit(limit)
        ).all()
        return [_row_to_sql_visit(row) for row in rows]

    def get_visit_count(self, venue_name: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(VenueVisitRow)
                .where(
                    VenueVisitRow.world_id == self.world_id,
                    VenueVisitRow.venue_name == venue_name,
                )
            )
            or 0
        )

    def get_favorite_venues(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(
                VenueVisitRow.venue_name,
                func.count().label("visit_count"),
                func.coalesce(func.avg(VenueVisitRow.rating), 0).label("avg_rating"),
                func.max(VenueVisitRow.visited_at).label("last_visited"),
                func.sum(VenueVisitRow.spent).label("total_spent"),
            )
            .where(VenueVisitRow.world_id == self.world_id)
            .group_by(VenueVisitRow.venue_name)
            .order_by(
                func.count().desc(),
                func.coalesce(func.avg(VenueVisitRow.rating), 0).desc(),
                func.max(VenueVisitRow.visited_at).desc(),
            )
            .limit(limit)
        ).all()
        return [
            {
                "venueName": row.venue_name,
                "avgRating": row.avg_rating,
                "lastVisited": row.last_visited,
                "totalSpent": row.total_spent,
                "metadata": {"visitCount": row.visit_count},
            }
            for row in rows
        ]

    def generate_experience_feedback(self, venue_name: str, items: list[str] | None = None) -> str:
        history = self.get_visit_history(venue_name, limit=5)
        count = self.get_visit_count(venue_name)
        item_text = "、".join(items or []) or "这次安排"
        if not history:
            return f"第一次去 {venue_name}，可以关注 {item_text} 的实际体验。"
        avg_spent = sum(visit["spent"] for visit in history) / len(history)
        return f"{venue_name} 已访问 {count} 次，最近平均花费约 {avg_spent:.0f} 元，适合安排 {item_text}。"
