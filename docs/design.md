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

Python 3.12 · FastAPI · asyncpg with hand-written SQL · yoyo-migrations · uv · pytest + httpx · ffprobe (ffmpeg) for audio duration · ULID ids.

## 4. Tables (phase 1)

Postgres holds metadata and text. Audio bytes live in the file store.

**`sessions`** — `id` text PK (ULID) · `txn_id` text null, partner's own reference, unique where not null · `status` text (`active` | `archived`) · `metadata` jsonb (≤ 4 KB, pass-through) · `created_at` · `archived_at` null

**`sources`** — `id` PK · `session_id` FK cascade · `kind` · `status` · `created_at` · `input` (`chunked` | `file`) · `format` · `language_hints` text[] · `stt_model` · `recording_started_at` · `recording_ended_at` · `completed_at` · `chunks_expected` int null · `warnings` jsonb `[]` · `failure` jsonb null · `cancel_reason` null · `transcript_text` text null · `transcript_language` null · `transcript_duration_ms` null · `transcript_created_at` null

**`chunks`** — `source_id` FK cascade + `index` int, PK together · `status` (`queued` | `success` | `failed`) · `received_at` · `recorded_at` null · `duration_ms` null · `size_bytes` · `text` null

Computed on read, not stored: `chunks.received`, `chunks.transcribed`, `audio_offset_ms` (sum of `duration_ms` of chunks `0 … n−1`, `null` if any is missing).

Open for review: transcript columns on `sources` versus a separate `transcripts` table; `warnings` as JSON on the source versus a `source_warnings` table.

### Lipi extensions to protocol objects

Lipi may add optional fields to protocol objects and requests. A protocol-only client never sends them and ignores them in responses. Each one is listed here so it stays deliberate and can be proposed upstream if it proves general.

| Object | Field | Meaning |
|---|---|---|
| Session | `txn_id` | Optional on `POST /v1/sessions`, returned on the session. The partner's own reference. Unique per deployment. Filter `GET /v1/sessions?txn_id=` from phase 3. |

Lipi does not change the meaning, type or value list of a protocol field, does not make a Lipi field required, and does not read inside `metadata`.

## 5. File store

`core/storage.py`: `put(key, bytes)`, `get(key)`, `delete(key)`, `delete_prefix(prefix)`. Disk implementation, root `LIPI_STORAGE_ROOT`, atomic writes (temp name, then rename).

Keys are derived from row ids, never stored:

```
sessions/{session_id}/sources/{source_id}/chunks/{index}.audio
sessions/{session_id}/sources/{source_id}/file.audio
```

## 6. Config

Environment variables, read once into one typed object; `env.example` lists them all.

`LIPI_DATABASE_URL` · `LIPI_STORAGE_ROOT` · `LIPI_BASE_URL` · `LIPI_SERVICE_NAME` · `LIPI_STT_MODELS` (comma-separated ids, first is default) · `LIPI_AUDIO_FORMATS` · `LIPI_MAX_CHUNK_SECONDS` · `LIPI_MAX_SECONDS` · `LIPI_INACTIVITY_SECONDS` · `LIPI_MAX_SOURCES_PER_SESSION` · `LIPI_MAX_AUDIO_SOURCES` · echo's own variables.

## 7. How a recording runs (phase 1)

1. `POST /v1/sessions/{id}/sources` `{kind: audio}` → `sources` row in `created`; response carries a `put` transport pointing at this server.
2. `PUT …/chunks/{n}` → refuse if the source is past `recording`, `Content-Type` ≠ `format`, or body empty → bytes to the file store → duration via ffprobe (refuse over `max_chunk_seconds`) → `chunks` row `queued`; source to `recording` on the first chunk → `agents.stt.transcribe(bytes, format, hints, model)` → `text` + `success`, or `failed` + `chunk_skipped` warning on the source → respond with the chunk object.
3. `POST …/end` → compute `gaps` against `chunks_total` (or the highest index); store `recorded_at` → gaps: respond, stay `recording` → no gaps: `processing`, join chunk texts in index order skipping `failed`, fill transcript columns, `success`. Idempotent past `recording`.
4. `GET …/transcript` → from the `sources` row; `409 invalid_state` before `success`.

Transcription runs inside the request in phase 1. Phase 2 moves it to a background task; shapes do not change.

## 8. Decisions

1. The protocol is the contract; it changes in its own repository first.
2. Core first. No plugin host, registry or manifest in v1. Plain interfaces inside the code where a swap is near-certain (file store, sign-in, agents).
3. Build in vertical slices through the protocol, thinnest first.
4. One database, Postgres. Metadata and text in Postgres; audio bytes in the file store; keys derived from ids.
5. Stack as in §3. Plain SQL with dataclass rows; no ORM.
6. Transcription inline in phase 1; background in phase 2.
7. v1 is chunked and file input only; no streaming audio.
8. Not multi-tenant.
9. Chunk duration measured with ffprobe on arrival.
10. Agents take plain inputs and return plain outputs; they do not read the database.
11. Tests: Docker Postgres, one test database, tables truncated between tests.
12. Lipi may add optional fields on top of protocol objects (§4 "Lipi extensions"); never required ones, never changes to existing ones. First: `txn_id` on sessions.
