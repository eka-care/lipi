import httpx
from helpers import assert_matches

PATH = "/.well-known/scribe-exchange"


async def test_discovery_matches_schema(client: httpx.AsyncClient) -> None:
    """protocol §4.1–4.2"""
    response = await client.get(PATH)
    assert response.status_code == 200
    assert_matches(response, "04-discovery")


async def test_discovery_declares_no_auth(client: httpx.AsyncClient) -> None:
    """protocol §4.3 auth: null means no authentication required"""
    response = await client.get(PATH)
    assert response.json()["auth"] is None


async def test_discovery_lists_audio_as_the_only_source_kind(client: httpx.AsyncClient) -> None:
    """protocol §4.3 sources.kinds: a kind not listed is refused; audio MUST be present"""
    response = await client.get(PATH)
    assert set(response.json()["capabilities"]["sources"]["kinds"]) == {"audio"}


async def test_discovery_lists_configured_stt_models_first_as_default(client: httpx.AsyncClient) -> None:
    """protocol §4.3 models: exactly one per list SHOULD be default"""
    stt = (await client.get(PATH)).json()["models"]["stt"]
    assert [model["id"] for model in stt] == ["stt-a", "stt-b"]
    assert [model["default"] for model in stt] == [True, False]


async def test_discovery_lists_configured_languages(client: httpx.AsyncClient) -> None:
    """protocol §4.3 languages: BCP 47 tags the service can transcribe"""
    languages = (await client.get(PATH)).json()["languages"]
    assert languages["supported"] == ["en", "hi"]
