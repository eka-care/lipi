from dataclasses import dataclass
from datetime import datetime

from lipi.core import db
from lipi.core.ids import new_id


@dataclass
class Session:
    id: str
    client_session_id: str | None
    status: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


async def insert(client_session_id: str | None, metadata: dict) -> Session:
    row = await db.fetchrow(
        "INSERT INTO sessions (id, client_session_id, metadata) VALUES ($1, $2, $3) RETURNING *",
        new_id(),
        client_session_id,
        metadata,
    )
    return Session(**row)


async def get(id: str) -> Session | None:
    row = await db.fetchrow("SELECT * FROM sessions WHERE id = $1", id)
    if row is None:
        return None
    return Session(**row)
