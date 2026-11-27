from typing import Any

import asyncpg
import orjson

_pool: asyncpg.Pool | None = None


async def _set_codecs(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        "jsonb",
        schema="pg_catalog",
        encoder=lambda value: orjson.dumps(value).decode(),
        decoder=orjson.loads,
    )


async def connect(url: str) -> None:
    global _pool
    _pool = await asyncpg.create_pool(url, init=_set_codecs)


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
    _pool = None


async def fetch(sql: str, *args: Any) -> list[asyncpg.Record]:
    return await _pool.fetch(sql, *args)


async def fetchrow(sql: str, *args: Any) -> asyncpg.Record | None:
    return await _pool.fetchrow(sql, *args)


async def execute(sql: str, *args: Any) -> str:
    return await _pool.execute(sql, *args)
