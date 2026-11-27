import httpx
from helpers import assert_matches


async def test_create_session_answers_201_active_and_empty(client: httpx.AsyncClient) -> None:
    """protocol §6.3: response 201 with the session: active, empty"""
    response = await client.post("/v1/sessions", json={})
    assert response.status_code == 201
    assert_matches(response, "06-session")
    body = response.json()
    assert body["status"] == "active"
    assert body["sources"] == []
    assert body["document_ids"] == []


async def test_create_session_returns_metadata_unchanged(client: httpx.AsyncClient) -> None:
    """protocol §6.2: metadata is client pass-through, returned unchanged"""
    metadata = {"visit_ref": "V-2026-1042", "nested": {"list": [1, "two", None]}, "name": "राम"}
    response = await client.post("/v1/sessions", json={"metadata": metadata})
    assert_matches(response, "06-session")
    assert response.json()["metadata"] == metadata


async def test_create_session_with_metadata_over_4kb_answers_metadata_too_large(client: httpx.AsyncClient) -> None:
    """protocol §6.10: metadata_too_large, 400, > 4 KB"""
    response = await client.post("/v1/sessions", json={"metadata": {"note": "x" * 4096}})
    assert response.status_code == 400
    assert_matches(response, "11-error")
    assert response.json()["error"]["code"] == "metadata_too_large"


async def test_create_session_with_malformed_body_answers_invalid_request(client: httpx.AsyncClient) -> None:
    """protocol §11.1: every error response is JSON of this shape (decision 19)"""
    response = await client.post("/v1/sessions", content=b'{"metadata": ', headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert_matches(response, "11-error")
    assert response.json()["error"]["code"] == "invalid_request"


async def test_get_session_returns_the_created_session(client: httpx.AsyncClient, session: dict) -> None:
    """protocol §6.3: GET /v1/sessions/{id}"""
    response = await client.get(f"/v1/sessions/{session['id']}")
    assert response.status_code == 200
    assert_matches(response, "06-session")
    assert response.json() == session


async def test_get_unknown_session_answers_session_not_found(client: httpx.AsyncClient) -> None:
    """protocol §6.10: session_not_found, 404, unknown id"""
    response = await client.get("/v1/sessions/01J9ZM1A2B3C4D5E6F7G8H9J0K")
    assert response.status_code == 404
    assert_matches(response, "11-error")
    assert response.json()["error"]["code"] == "session_not_found"


async def test_create_session_returns_client_session_id(client: httpx.AsyncClient) -> None:
    """design.md §4 Lipi extensions: client_session_id is returned on the session"""
    response = await client.post("/v1/sessions", json={"client_session_id": "visit-42"})
    assert_matches(response, "06-session")
    assert response.json()["client_session_id"] == "visit-42"


async def test_create_session_with_client_session_id_over_50_characters_answers_invalid_request(
    client: httpx.AsyncClient,
) -> None:
    """design.md §4 Lipi extensions: client_session_id is at most 50 characters"""
    response = await client.post("/v1/sessions", json={"client_session_id": "x" * 51})
    assert response.status_code == 400
    assert_matches(response, "11-error")
    assert response.json()["error"]["code"] == "invalid_request"
