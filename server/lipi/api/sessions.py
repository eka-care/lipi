import orjson
from fastapi import APIRouter
from pydantic import BaseModel, Field

from lipi.core.errors import LipiError
from lipi.store import sessions
from lipi.store.sessions import Session

router = APIRouter(prefix="/v1/sessions")

MAX_METADATA_BYTES = 4096  # protocol §6.2: metadata max 4 KB


class SessionCreate(BaseModel):
    metadata: dict = {}
    # design §4: Lipi extension, the partner's own id; not unique
    client_session_id: str | None = Field(default=None, min_length=1, max_length=50)


def to_session(row: Session, sources: list[dict]) -> dict:
    return {
        "id": row.id,
        "client_session_id": row.client_session_id,
        "status": row.status,
        "metadata": row.metadata,
        "created_at": row.created_at,
        "archived_at": row.archived_at,
        "sources": sources,
        "document_ids": [],
    }


@router.post("", status_code=201)
async def create_session(body: SessionCreate | None = None) -> dict:
    # protocol §6.3: metadata is optional, so the body may be absent
    body = body or SessionCreate()
    if len(orjson.dumps(body.metadata)) > MAX_METADATA_BYTES:
        raise LipiError("metadata_too_large", 400, "metadata is larger than 4 KB. Send a smaller object.")
    row = await sessions.insert(body.client_session_id, body.metadata)
    return to_session(row, [])


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    row = await sessions.get(session_id)
    if row is None:
        raise LipiError("session_not_found", 404, f"There is no session {session_id}.")
    return to_session(row, [])
