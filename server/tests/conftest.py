import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
from yoyo import get_backend, read_migrations

TEST_DATABASE_URL = os.environ.get("LIPI_TEST_DATABASE_URL", "postgresql://lipi:lipi@localhost:5434/lipi_test")
MIGRATIONS = Path(__file__).resolve().parents[1] / "lipi" / "migrations"

# Fixed values so tests do not depend on a developer's .env.
os.environ.update(
    {
        "LIPI_DATABASE_URL": TEST_DATABASE_URL,
        "LIPI_STORAGE_ROOT": tempfile.mkdtemp(prefix="lipi-test-"),
        "LIPI_BASE_URL": "http://test",
        "LIPI_SERVICE_NAME": "Lipi (test)",
        "LIPI_STT_MODELS": "stt-a,stt-b",
        "LIPI_LANGUAGES": "en,hi",
        "LIPI_AUDIO_FORMATS": "audio/webm;codecs=opus,audio/wav,audio/ogg;codecs=opus",
        "LIPI_MAX_CHUNK_SECONDS": "25",
        "LIPI_MAX_SECONDS": "7200",
        "LIPI_INACTIVITY_SECONDS": "300",
        "LIPI_MAX_SOURCES_PER_SESSION": "20",
        "LIPI_MAX_AUDIO_SOURCES": "3",
    }
)

from lipi.core import db  # noqa: E402  (after the environment is set)
from lipi.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated() -> None:
    backend = get_backend(TEST_DATABASE_URL.replace("postgresql:", "postgresql+psycopg:", 1))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(read_migrations(str(MIGRATIONS))))


@pytest.fixture(scope="session")
async def client(migrated: None) -> AsyncGenerator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture(autouse=True)
async def empty_tables(client: httpx.AsyncClient) -> None:
    await db.execute("TRUNCATE sessions, sources, chunks CASCADE")
