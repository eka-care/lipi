import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    storage_root: str
    base_url: str
    service_name: str
    stt_models: list[str]
    languages: list[str]
    audio_formats: list[str]
    max_chunk_seconds: int
    max_seconds: int
    inactivity_seconds: int
    max_sources_per_session: int
    max_audio_sources: int


def _read(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set. Copy env.example to .env and fill it in.")
    return value


def _read_list(name: str) -> list[str]:
    return [item.strip() for item in _read(name).split(",") if item.strip()]


def _read_int(name: str) -> int:
    value = _read(name)
    if not value.isdigit():
        raise RuntimeError(f"{name} must be a whole number; it is {value!r}.")
    return int(value)


def load() -> Config:
    return Config(
        database_url=_read("LIPI_DATABASE_URL"),
        storage_root=_read("LIPI_STORAGE_ROOT"),
        base_url=_read("LIPI_BASE_URL").rstrip("/"),
        service_name=_read("LIPI_SERVICE_NAME"),
        stt_models=_read_list("LIPI_STT_MODELS"),
        languages=_read_list("LIPI_LANGUAGES"),
        audio_formats=_read_list("LIPI_AUDIO_FORMATS"),
        max_chunk_seconds=_read_int("LIPI_MAX_CHUNK_SECONDS"),
        max_seconds=_read_int("LIPI_MAX_SECONDS"),
        inactivity_seconds=_read_int("LIPI_INACTIVITY_SECONDS"),
        max_sources_per_session=_read_int("LIPI_MAX_SOURCES_PER_SESSION"),
        max_audio_sources=_read_int("LIPI_MAX_AUDIO_SOURCES"),
    )
