# Lipi — design

Owner: Neha Jagadeesh (Eka Care) · Status: draft

## 1. What Lipi is

An open-source agentic scribe: a recording (or a pasted note, or a file) in, a structured document out, following a template, on infrastructure you run. Any field; the templates set the domain.

Lipi is the reference implementation of the **Scribe Exchange Protocol** (`github.com/eka-care/scribeexchangeprotocol`). The protocol is the contract: every object, endpoint, status and error code comes from there. Lipi adds only what the protocol leaves to implementations (users, settings, administration).

Built on **echo** (`eka-care/echo-sdk`) for speech-to-text and the writing agent; Parrotlet and other models come through echo.

Licence Apache-2.0, DCO for contributions, Eka Care merges.

## 2. Repository layout

```
lipi/
  CLAUDE.md                 rules for build sessions
  docs/design.md            this file
  docs/phases.md            build phases
  .claude/skills/           lipi-code-style, lipi-testing
  server/
    pyproject.toml          uv
    lipi/
      main.py               app, mounts routers, error handler
      core/                 config.py  db.py  errors.py  ids.py  storage.py
      store/                one file per table, plain SQL functions returning dataclass rows
      api/                  one file per protocol concept, routes only
      agents/               the only place echo is imported: stt.py (later generate.py)
      migrations/           yoyo SQL files, numbered
    tests/
      conftest.py  audio/  test_<chapter>.py
  scripts/demo.sh
  docker-compose.yml  env.example  Makefile
```

### Boundaries

| Folder | Does | Imports from |
|---|---|---|
| `core/` | config, DB pool, error type, ULIDs, file store | nothing in `lipi` |
| `store/` | SQL for one table per file; returns `@dataclass` rows; no rules, no classes | `core/` |
| `agents/` | calls echo; plain inputs in, plain outputs out | `core/` |
| `api/` | validates the request (Pydantic), calls `store/` and `agents/`, builds the protocol object | `core/`, `store/`, `agents/` |

Three representations only: Pydantic request models in `api/`, dataclass rows in `store/`, protocol JSON built by one `to_<object>()` function per object in `api/`.

No `services/`, `managers/`, `handlers/`, `utils/`.

## 3. Stack

Python 3.12 · FastAPI · asyncpg with hand-written SQL · yoyo-migrations · uv · pytest + httpx · ULID ids.

### Libraries

A newer or faster library is chosen when it removes code or a cost we can measure. CPU work inside a request holds the server's one thread, so JSON we encode or decode ourselves uses the fast library.

| Need | Chosen | Instead of | Why |
|---|---|---|---|
| Web framework | FastAPI | Flask, Django | async, typed requests, OpenAPI generated |
| Response and request JSON | Pydantic v2 (through FastAPI) | orjson response class, msgspec | Pydantic's Rust core already serialises responses; FastAPI deprecated its orjson response class in 0.131 |
| JSON we handle ourselves (jsonb columns, size checks) | orjson | standard `json` | several times faster; this work runs on the request thread |
| Server | uvicorn[standard] | plain uvicorn | includes uvloop and httptools |
| Postgres driver | asyncpg | psycopg | fastest async driver |
| Migrations | yoyo-migrations (with psycopg, migrations only) | Alembic, own runner | plain SQL files; locking and applied-tracking done for us |
| IDs | python-ulid | UUID | the protocol's ids are ULIDs |
| Config | hand-written dataclass | pydantic-settings | fifty lines, no dependency |
| Logging | standard `logging` | structlog | enough for now; revisit in the operations phase |
| Lint and format | ruff | black, flake8, isort | one fast tool |
| Packaging | uv | pip, poetry | fast, lockfile |
| Tests | pytest, pytest-asyncio, httpx, jsonschema | — | tests run through HTTP and validate against the protocol schemas |

### Typing

- A function that `yield`s is annotated as a generator: `AsyncGenerator[T]` or `Generator[T]` from `collections.abc`, not `AsyncIterator` or `Iterator`. The type checker marks `@asynccontextmanager` on a function annotated with `AsyncIterator` as deprecated.
- Type hints come from `collections.abc` and the built-in generics (`list[str]`, `X | None`), not from `typing.List` or `typing.Optional`. ruff's `UP` rules enforce this.

## 4. Tables (phase 1)

Postgres holds metadata. Content lives in the file store: audio bytes, chunk text, transcript text.

**`sessions`** — `id` text PK (ULID) · `client_session_id` text null, the partner's own id for the session, at most 50 characters, not unique (a plain index; lookup returns all matches) · `status` text (`active` | `archived`) · `metadata` jsonb (≤ 4 KB, pass-through) · `created_at` · `updated_at` · `archived_at` null

**`sources`** — `id` PK · `session_id` FK cascade · `kind` · `status` · `created_at` · `input` (`chunked` | `file`) · `format` · `language_hints` text[] · `stt_model` · `recording_started_at` · `recording_ended_at` · `completed_at` · `chunks_expected` int null · `warnings` jsonb `[]` · `failure` jsonb null · `cancel_reason` null · `transcript_language` null · `transcript_duration_ms` null · `transcript_created_at` null

**`chunks`** — `source_id` FK cascade + `index` int, PK together · `status` (`queued` | `success` | `failed`) · `received_at` · `recorded_at` null · `duration_ms` null · `size_bytes`

Computed on read, not stored: `chunks.received`, `chunks.transcribed`, `audio_offset_ms` (sum of `duration_ms` of chunks `0 … n−1`, `null` if any is missing or has no known duration).

`sources` is one table for every kind; columns that belong to one kind are null for the others. The transcript's facts (language, duration, created time) are columns on `sources`; its text is a file. `warnings` is a JSON list on the source.

A whole-file upload (`input: file`) has its own flow and no `chunks` rows: the file is stored as `file.audio`, transcribed in one call, and its text written straight to `transcript.txt`.

### Lipi extensions to protocol objects

Lipi may add optional fields to protocol objects and requests. A protocol-only client never sends them and ignores them in responses. Each one is listed here so it stays deliberate and can be proposed upstream if it proves general.

| Object | Field | Meaning |
|---|---|---|
| Session | `client_session_id` | Optional on `POST /v1/sessions`, returned on the session. The partner's own id for the session, at most 50 characters. Not unique; lookup returns all matches. For lookup only: `GET /v1/sessions?client_session_id=` from phase 3, which returns every session that matches. Paths always use `id`. |

Lipi does not change the meaning, type or value list of a protocol field, does not make a Lipi field required, and does not read inside `metadata`.

## 5. File store

`core/storage.py`: `put(key, bytes)`, `get(key)`, `delete(key)`, `delete_prefix(prefix)`. Disk implementation, root `LIPI_STORAGE_ROOT`, atomic writes (temp name, then rename).

Keys are derived from row ids, never stored:

```
sessions/{session_id}/sources/{source_id}/chunks/{index}.audio
sessions/{session_id}/sources/{source_id}/chunks/{index}.txt
sessions/{session_id}/sources/{source_id}/file.audio
sessions/{session_id}/sources/{source_id}/transcript.txt
```

File reads and writes run on helper threads (`asyncio.to_thread`); at `end` the chunk texts are read in parallel.

## 6. Config

Environment variables, read once into one typed object; `env.example` lists them all.

`LIPI_DATABASE_URL` · `LIPI_STORAGE_ROOT` · `LIPI_BASE_URL` · `LIPI_SERVICE_NAME` · `LIPI_STT_MODELS` (comma-separated ids, first is default) · `LIPI_LANGUAGES` (BCP 47 tags the service transcribes) · `LIPI_AUDIO_FORMATS` · `LIPI_MAX_CHUNK_SECONDS` · `LIPI_MAX_SECONDS` · `LIPI_INACTIVITY_SECONDS` · `LIPI_MAX_SOURCES_PER_SESSION` · `LIPI_MAX_AUDIO_SOURCES` · echo's own variables.

## 7. How a recording runs (phase 1)

1. `POST /v1/sessions/{id}/sources` `{kind: audio}` → `sources` row in `created`; response carries a `put` transport pointing at this server.
2. `PUT …/chunks/{n}` → refuse if the source is past `recording`, `Content-Type` ≠ `format`, or body empty → bytes to the file store → `chunks` row `queued`; source to `recording` on the first chunk → `agents.stt.transcribe(bytes, format, hints, model)` returns text, language and duration → duration over `max_chunk_seconds`: chunk `failed` + `chunk_skipped` warning; otherwise `text`, `duration_ms`, `success`; transcription raised: `failed` + `chunk_skipped` warning → respond with the chunk object. For `input: file`, a duration over `max_seconds` fails the source with `audio_too_long`.
3. `POST …/end` → compute `gaps` against `chunks_total` (or the highest index); store `recorded_at` → gaps: respond, stay `recording` → no gaps: `processing`, read the chunk text files in parallel, join them in index order skipping `failed`, write `transcript.txt`, fill the transcript columns, `success`. Idempotent past `recording`.
4. `GET …/transcript` → from the `sources` row; `409 invalid_state` before `success`.

Transcription runs inside the request in phase 1. Phase 2 moves it to a background task; shapes do not change.

## 8. Decisions

1. The protocol is the contract; it changes in its own repository first.
2. Core first. No plugin host, registry or manifest in v1. Plain interfaces inside the code where a swap is near-certain (file store, sign-in, agents).
3. Build in vertical slices through the protocol, thinnest first.
4. One database, Postgres, for metadata. Content (audio bytes, chunk text, transcript text) lives in the file store; keys derived from ids, never stored.
5. Stack as in §3. Plain SQL with dataclass rows; no ORM.
6. Transcription inline in phase 1; background in phase 2.
7. v1 is chunked and file input only; no streaming audio.
8. Not multi-tenant.
9. Audio duration comes from speech-to-text: `agents.stt.transcribe` returns it with the text, and echo returns it. Lipi runs no audio tool of its own and starts no subprocess. Length limits are checked after transcription.
10. Agents take plain inputs and return plain outputs; they do not read the database.
11. Tests: Docker Postgres, one test database, tables truncated between tests.
12. Lipi may add optional fields on top of protocol objects (§4 "Lipi extensions"); never required ones, never changes to existing ones. First: `client_session_id` on sessions.
13. Discovery fields that the protocol schema requires but that have no `LIPI_*` variable are constants in `api/discovery.py` until their phase arrives. The values are Lipi's own defaults, not taken from the protocol: the protocol leaves these limits to each service, and its example values are only an illustration. Each becomes a `LIPI_*` variable, set per deployment, in the phase that enforces it: `templates` limits in phase 4, `documents` limits and `output_formats` in phase 5. Until then no code checks them, so a setting would only change what discovery says. Current values: `templates {max_instruction_chars: 20000, max_per_caller: 50}`, `documents {max_content_bytes: 1048576}` (1 MiB), `output_formats: ["markdown"]`, `languages.auto_detection: true`, one placeholder structuring model `none`. An stt model's `display_name` is its id. `endpoints.base_url` is `LIPI_BASE_URL` + `/v1`.
14. yoyo-migrations cannot use asyncpg, so `psycopg` is a dependency for migrations only. `make migrate` and the tests rewrite `postgresql:` to `postgresql+psycopg:` for yoyo. The app itself uses asyncpg only.
15. echo comes from a local checkout for now (`[tool.uv.sources]`, `../../../../0_agent_core/echo-sdk`, package name `echo`). This breaks "fresh clone → `uv sync`" for anyone without that checkout; it has to move to a git or PyPI source before Lipi is published.
16. Docker Postgres creates `lipi` and `lipi_test` (`docker/initdb.sql`). Local ports are 5434 (Postgres) and 8100 (server), to stay clear of other local services on 5432, 5433 and 8000.
17. Libraries are chosen by the rule and table in §3. JSON handled by Lipi's own code uses orjson; responses stay with Pydantic.
18. echo comes from git, `github.com/eka-care/echo-sdk`, branch `main` (`[tool.uv.sources]`, package name `echo`). It replaces decision 15's local path, so a fresh clone can `uv sync`.
19. An unknown route or a wrong method answers `400 invalid_request` in the protocol's error shape. 400 rather than 404 because §11.3 pairs `invalid_request` with 400. FastAPI's request-validation error also answers `400 invalid_request`, unless a route maps it to its chapter's own code.
20. Audio duration is not required for now. `agents.stt.transcribe` may return no duration; then the chunk's `duration_ms` and `audio_offset_ms` are `null`, and the `max_chunk_seconds` and `max_seconds` checks are skipped. This narrows decision 9. To be revisited before Step 6.
21. Type hints follow §3 "Typing". Generator functions are annotated `AsyncGenerator`/`Generator`, so the type checker raises no deprecation warning on `@asynccontextmanager`.
22. Tables: `sessions` has `updated_at` and `client_session_id` (lookup only, plain index). `sources` is one table for all kinds. A whole-file upload has its own flow, without chunk rows. The transcript's detected language is filled for whole-file uploads and left `null` for chunked recordings for now. An owner column arrives with users in phase 6.
23. Chunk text and transcript text are files, read in parallel at `end`. A database copy of chunk text is added only if a measured delay calls for it.
24. The transcript's `duration_ms` is nullable. The protocol is changed to say so (chapter 8 and its schema) in the protocol repository.
25. Sessions (Step 2):
    - `client_session_id` is not unique. A plain index serves the phase 3 lookup, which returns every session that matches. Creating a session never checks whether the id was used before.
    - Unknown fields in a request body are ignored, not refused.
    - A `POST /v1/sessions` with no body is the same as `{}`.
    - `metadata` over 4 KB means more than 4096 bytes in its compact UTF-8 JSON form.
    - `client_session_id` is always present on the session, `null` when not given; it must be 1–50 characters.
    - Other HTTP errors raised by the framework keep their real status, with a §11 body and the code that §11.3 gives that status: 401 `authentication_failed`, 403 `forbidden`, 413 `payload_too_large`, 429 `rate_limited`, 503 `unavailable`. Any other 4xx gets `invalid_request`; any other status gets `internal_error`. 404 and 405 stay as in decision 19.
