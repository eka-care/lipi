---
name: lipi-testing
description: How tests are written in the Lipi repository. Read before writing or changing any test.
---

# Lipi testing

Tests prove the server does what the protocol says. A test with no rule behind it is not written.

## One test, one rule

- Each test proves one sentence from the protocol or one line of the phase's "done when".
- The name is that rule as a sentence: `test_end_with_missing_chunk_reports_gap_and_stays_recording`.
- The docstring cites it: `"""protocol §6.8"""`. If you cannot cite it, you are testing your implementation, not the contract: do not write it.

## How a test runs

- Through HTTP with `httpx.AsyncClient` against the app. Never call routes, store functions or helpers directly.
- Real Postgres (Docker), one test database, tables truncated between tests. Real disk on a temporary directory. Never mock either.
- The only fake: `agents.stt.transcribe`, replaced in `conftest.py` with one that returns fixed text per chunk and can be told to raise for an index.
- Real audio in `tests/audio/`: one short file per accepted format, one deliberately unreadable.

## Every response is checked against the schema

`conftest.py` loads the JSON schemas from the protocol repository (`LIPI_PROTOCOL_SCHEMAS`, default `../scribeexchangeprotocol/schemas`). `assert_matches(response, "06-source")` validates the body. Every test that reads a protocol object calls it; errors are validated against `11-error` and asserted on status and `error.code`.

## Layout

One test file per protocol chapter (`test_discovery.py`, `test_sessions.py`, `test_sources.py`, `test_audio.py`, `test_transcripts.py`), tests in the order the rules appear in the chapter.

Fixtures are named for the state they produce and go through HTTP: `session`, `audio_source`, `recording_source`, `ended_source`.

## Not written

- Tests of private functions, store functions or `to_*()` builders on their own.
- Assertions on database rows, file names or log lines.
- Snapshot tests of whole bodies.
- A test per code branch.
- Parametrisation over values the rule does not distinguish. Parametrise only where the spec lists the values.

## When a test fails

Read the cited sentence. Fix whichever of code or test disagrees with it. If the protocol itself looks wrong, stop and say so.
