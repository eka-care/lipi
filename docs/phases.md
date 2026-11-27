# Build phases

One phase per session. The session reads `CLAUDE.md`, then its phase here, then `design.md` and the protocol chapters named. Nothing is built ahead of its phase.

| Phase | Slice | Protocol chapters |
|---|---|---|
| **1** | A recording lands and is transcribed | 4, 6 (audio), 7, 8, 11 |
| 2 | Service-side ending (inactivity, max length), background transcription, cancel, delete | 6 |
| 3 | Text, file, reference sources; session list, archive | 6 |
| 4 | Templates | 9 |
| 5 | Generate (streamed) and documents | 10 |
| 6 | Sign-in, users, bearer tokens; discovery `auth` | 5 |
| 7 | Settings, administration, operations | — |
| F1… | SDK and web app, trailing the backend | — |

---

## Phase 1 — a recording lands and is transcribed

> **Status (2026-11-27, after Step 2)**
> - **Done:**
>   - Step 1, the skeleton: config, db pool, `LipiError` and its handlers, ULIDs, `001_initial.sql`, app with request logging, discovery, compose, `env.example`, Makefile, conftest. Decisions 13–16.
>   - Step 1 fixes:
>     - echo from git.
>     - Unknown route, wrong method and request-validation errors answer `400 invalid_request` in the §11 shape.
>     - A 500 still writes the request log line.
>     - `LIPI_LANGUAGES`.
>     - orjson codec for jsonb.
>     - ruff and `make lint`.
>     - FastAPI ≥ 0.165.
>     - `tests/helpers.py`.
>     - `db.connect`.
>
>     Decisions 18–20.
>   - Step 2, sessions:
>     - `001_initial.sql` edited to match `design.md` §4, and local databases recreated.
>     - `store/sessions.py` and `api/sessions.py`: `POST /v1/sessions` and `GET /v1/sessions/{id}`.
>     - `client_session_id`, not unique.
>     - `errors.no_route` turns only 404 and 405 into `invalid_request`; other HTTP errors keep their status.
>
>     Decision 25.
>   - `make lint` is clean and `make test` is green (15 tests). `make demo` prints discovery, creates a session and reads it back.
> - **Deferred:**
>   - Fake `agents.stt.transcribe` in conftest → Step 5, together with `agents/stt.py`.
>   - echo provider extras → Step 5.
>   - `demo.sh` covers discovery and sessions; it grows with each step.
>   - Decision 20 (optional duration) is to be revisited before Step 6.
> - **Open:** none.

**Goal:** with `curl` and a folder of short audio files: create a session, start a recording, upload numbered chunks, end it, read the transcript.

**Reads:** `design.md`; protocol §4, §6, §7, §8, §11; skills `lipi-code-style`, `lipi-testing`.

### Build, in this order (each step runnable and tested before the next)

**Step 1 — Skeleton**
- `server/pyproject.toml`: uv; fastapi, uvicorn, asyncpg, yoyo-migrations, pydantic, a ULID library, echo-sdk; dev: pytest, pytest-asyncio, httpx, jsonschema.
- `core/config.py`: one typed object from the `LIPI_*` variables.
- `core/db.py`: asyncpg pool opened at startup; `fetch`, `fetchrow`, `execute`.
- `core/errors.py`: `LipiError(code, status, message, details=None)`; a handler that renders protocol §11 JSON.
- `core/ids.py`: `new_id()` returns a ULID.
- `migrations/001_initial.sql`: `sessions`, `sources`, `chunks` as in `design.md` §4; CHECKs on closed-list columns; cascade FKs; index `sources(session_id, created_at)`; partial index on `sessions.client_session_id` (not unique, decision 25).
- `main.py`: app, lifespan (pool open/close), routers, error handler, one log line per request.
- `api/discovery.py`: `GET /.well-known/scribe-exchange` from config; `auth: null`; `audio` the only source kind; `models.stt` from `LIPI_STT_MODELS`; one placeholder structuring model.
- `docker-compose.yml` (Postgres), `env.example`, `Makefile` (`dev`, `migrate`, `test`, `demo`).
- `tests/conftest.py`: app client; test database truncated between tests; temporary storage root; `assert_matches(response, schema_name)`; fake `agents.stt.transcribe`.
- Check: discovery validates against `04-discovery.schema.json`.

**Step 1 fixes — before Step 2**
- echo as a git or published dependency in `pyproject.toml`, so a fresh clone can `uv sync` (replaces decision 15's local path).
- Errors in the protocol's shape everywhere: FastAPI's request-validation error → `400` with a §11 body (`invalid_request`, or the chapter's own code where a route has one); unknown route and wrong method → §11 body. Which code an unknown route carries: ask Neha before building.
- A 500 still writes the per-request log line.
- `LIPI_LANGUAGES` in config, `env.example` and discovery `languages.supported`.
- orjson for the jsonb columns: an asyncpg type codec set when the pool opens (`orjson.dumps(...).decode()`, `orjson.loads`).
- ruff in the dev dependencies, configured in `pyproject.toml`; `make lint`.
- FastAPI minimum raised to the current release.
- `tests/helpers.py` holds `assert_matches`; tests import it from there.
- `core/db.py`: `open` renamed so it does not shadow the built-in.

**Step 2 — Sessions**
- `migrations/001_initial.sql` edited to match `design.md` §4 (nothing is deployed, so no second migration): `sessions.txn_id` → `client_session_id` (≤ 50 characters) with a plain, non-unique index; `sessions.updated_at`; `sources.transcript_text` removed; `chunks.text` removed. Local databases are recreated.
- `store/sessions.py`: `insert(client_session_id, metadata)`, `get(id)`; returns a `Session` dataclass.
- `api/sessions.py`: `POST /v1/sessions` (body `metadata?`, `client_session_id?`; over 4 KB → `metadata_too_large`; `client_session_id` over 50 characters → `invalid_request`; not unique, decision 25); `GET /v1/sessions/{id}` (`session_not_found`); `to_session(row, sources)`.

**Step 3 — Audio sources**
- `store/sources.py`: `insert_audio`, `get`, `list_for_session`, `set_status`, `append_warning`, `set_transcript`; returns a `Source` dataclass.
- `api/sources.py`: `POST …/sources` (`kind: audio`, `input`, `format`, `language_hints?`, `stt_model?`, `transports?`), validated against discovery (`invalid_source`, `kind_not_supported`, `source_limit_reached`), refused on an archived session (`invalid_state`); `GET …/sources`; `GET …/sources/{sid}`; `to_source(row, chunks)` with the `put` transport built from `LIPI_BASE_URL` and `chunks.received / expected / transcribed`.

**Step 4 — Upload, bytes only**
- `core/storage.py`: disk file store, atomic writes, keys as in `design.md` §5.
- `store/chunks.py`: `upsert`, `get`, `list_for_source`, `set_success`, `set_failed`, `set_recorded_at`; returns a `Chunk` dataclass.
- `api/chunks.py`: `PUT …/chunks/{n}` — state check (`source_not_recording`), `Content-Type` check (`format_mismatch`), empty body (`payload_required`), write bytes, row `queued`, source to `recording` with `recording_started_at` on the first chunk, respond with the chunk object. `PUT …/file` for `input: file`: bytes to `file.audio`, source to `recording`; no chunk row. `GET …/transcript/chunks/{n}` (`chunk_not_found`). `to_chunk(row, offset_ms)`.

**Step 5 — Transcription**
- `agents/stt.py`: `transcribe(audio, format, language_hints, model) -> (text, language, duration_ms)` through echo.
- Wired into the upload: text → written to `chunks/{n}.txt`, chunk `success` with `duration_ms`; duration over `max_chunk_seconds`, or an exception → chunk `failed`, source warning `chunk_skipped`, one log line. The upload response carries the text.
- `input: file` is its own flow: at `end` the whole file is transcribed in one call and the text written to `transcript.txt`; duration over `max_seconds` → source `failed` with `audio_too_long`.
- The fake `transcribe` in conftest returns a duration too.

**Step 6 — End and transcript**
- `POST …/end` (`chunks_total?`, `recorded_at?`): idempotent past `recording`; store `recorded_at`; `gaps` = indexes missing below `chunks_total` (or below the highest received); gaps → respond, stay `recording`; none → `processing`, read the `success` chunk text files in parallel, join in index order, write `transcript.txt`, fill the transcript columns (language `null` for chunked recordings for now; duration = sum of chunk durations, `null` if any is unknown), `success`, `completed_at`.
- `api/transcripts.py`: `GET …/transcript` from the source row; `invalid_state` before `success`.

**Step 7 — Demo**
- `tests/audio/`: three short real files (webm/opus, wav, ogg) and one unreadable.
- `scripts/demo.sh`: discovery → session → source → three chunks out of order → `end` with a gap → the missing chunk → `end` → transcript printed.

**Tests:** `test_discovery.py` (§4), `test_sessions.py` (§6.2–6.3, `client_session_id`), `test_sources.py` (§6.4–6.8), `test_audio.py` (§7), `test_transcripts.py` (§8). Every "done when" line below has a named test.

### Decide during the phase (add to `design.md` §8)

- What `stt.transcribe` does when echo returns empty text (`success` with `""`) versus raises (`failed` + `chunk_skipped`).
- How `agents/stt.py` calls echo — read echo's STT interface and choose.
- Which echo STT provider `env.example` enables by default.

### Done when

- Fresh clone → `uv sync` → `docker compose up -d` → `make migrate` → `make dev` → discovery answers.
- `make demo` runs the flow against `tests/audio/` and prints the transcript.
- Chunk 3 before chunk 2, then `end` with `chunks_total: 4` → `gaps: [2]`, still `recording`; send chunk 2, `end` again → `success`.
- Same index uploaded twice → one chunk, second bytes.
- Unreadable chunk → chunk `failed`, source warning `chunk_skipped`, transcript assembles without it.
- `format` not in discovery → `400 invalid_source`; `Content-Type` ≠ `format` → `400 format_mismatch`; `end` on a `success` source is idempotent; transcript before `success` → `409 invalid_state`.
- Every response in the tests validates against `scribeexchangeprotocol/schemas/`.
- `make test` green.

### Must not

- Session list / `PATCH` / `DELETE`; source `cancel` / `DELETE` (phases 2–3).
- `text`, `file`, `reference` sources (phase 3).
- Any background process, timer or queue (phase 2).
- Auth, users, settings beyond config (phases 6–7).
- Templates, generate, documents (phases 4–5).
- Any plugin mechanism.

### Deferred

- Auto-end on inactivity and `max_seconds`: declared in discovery, enforced in phase 2.
- `post-form` transport.
