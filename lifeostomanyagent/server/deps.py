from __future__ import annotations

from collections.abc import Generator

from lifeostomanyagent.server.db.models import SessionLocal, get_db
from lifeostomanyagent.server.services import LifeOSService


def get_service() -> Generator[LifeOSService, None, None]:
    db = get_db()
    try:
        yield LifeOSService(db)
    finally:
        db.close()
