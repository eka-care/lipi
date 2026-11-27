import httpx
from helpers import assert_matches


async def test_unknown_route_answers_in_error_shape(client: httpx.AsyncClient) -> None:
    """protocol §11.1: every error response, from every endpoint, is JSON of this shape (decision 19)"""
    response = await client.get("/v1/no-such-thing")
    assert response.status_code == 400
    assert_matches(response, "11-error")
    assert response.json()["error"]["code"] == "invalid_request"


async def test_wrong_method_answers_in_error_shape(client: httpx.AsyncClient) -> None:
    """protocol §11.1: every error response, from every endpoint, is JSON of this shape (decision 19)"""
    response = await client.post("/.well-known/scribe-exchange")
    assert response.status_code == 400
    assert_matches(response, "11-error")
    assert response.json()["error"]["code"] == "invalid_request"
