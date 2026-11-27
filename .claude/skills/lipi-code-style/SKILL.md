---
name: lipi-code-style
description: How code is written in the Lipi repository — think first, smallest change, flat and plain. Read before writing or changing any code here.
---

# Lipi code style

Four behaviours, adapted from Andrej Karpathy's observations on how LLMs go wrong when coding (as collected in the `andrej-karpathy-skills` guidelines), plus the rules that are specific to this repository. Ask before acting beats acting fast.

## 1. Think before coding

- State your assumptions before you write. If something is uncertain, ask; do not guess silently.
- If a request can be read two ways, name both and ask which.
- If a simpler way exists than the one asked for, say so before building the asked-for one.
- If you are confused, stop and say what is unclear. Do not push through.
- Read the protocol chapter and the `design.md` section for the thing you are touching before you touch it.
- If the protocol and `design.md` disagree, the protocol wins; say so and stop.

## 2. Simplicity first

- Write the minimum code that solves the task in front of you. Nothing for a future phase.
- No abstraction for one use. A function used once is inlined. A class with one method is a function.
- No configurability that nobody asked for. No "it might be useful later".
- No handling for cases that cannot happen. Trust the protocol's state machine; check the state once, at the top of the route.
- No dead branches, no wrapper that only forwards, no variable used once.
- Prefer a plain function and a dict over a class, except the three representations in `design.md` §2 (Pydantic request models, dataclass rows, `to_*()` builders).
- Prefer a flat file inside its folder over a sub-package.

## 3. Surgical changes

- Change only what the task needs; leave unrelated code, comments and formatting alone. Anything your change makes wrong — a comment, a name, a now-unused function — fix it in the same change.
- Match the style that is already there, even where you would have done it differently.
- Unrelated dead code: mention it, do not delete it.
- Remove only the imports and functions that *your* change made unused.
- Never rename, move or "tidy" as a side effect.

## 4. Goal-driven

- Turn the task into a check you can run before you start: a failing test, a `curl` that must answer, a schema the response must validate against.
- For a multi-step task, pair every step with its check. Loop until the checks pass, then stop.
- "Done" is the check passing, not the code existing.

## Rules specific to this repository

- **Layout and boundaries: `design.md` §2.** Which folder owns what, which may import which, where each representation lives. If you feel the need for a new layer or folder, stop and ask.
- **Shallow.** At most two levels of nesting (an `if` inside a `for` is the limit); beyond that, split or flatten with early returns. A function over 40 lines or a file over 300 lines is a sign to stop and ask.
- **Early returns, no `else` after `return`.** Check the bad cases first and raise; the happy path is the straight line at the bottom.
- **One error type.** Every refusal is `raise LipiError(code, status, message)`. Codes come from protocol §11 only. No bare `HTTPException`, no custom exception hierarchy.
- **SQL parameters are always bound** (`$1`, `$2`). Never build SQL with f-strings.
- **echo is imported in `agents/` only.** Other modules call `agents.stt.transcribe(...)` and never see echo types.
- **Names from the protocol.** Fields, statuses, error codes and warning codes are spelled exactly as in the spec. No synonyms, no internal names leaking into responses.
- **No comments that say what the code says.** A comment explains *why*, cites the protocol section (`# protocol §6.8: gaps keep the source recording`), or is absent.
- **Type hints on every function signature.**
- **Async all the way.** No blocking calls in a route.
- **Logging.** One structured log line per request (method, path, status, duration) and one per failure in `agents/` (source id, chunk index, error). Never log audio bytes, request bodies or secrets.
- **Plain words in docs and messages.** Error `message` strings are a sentence a person can act on.

## Before you say you are done

1. Does every error path go through `LipiError` with a protocol code?
2. Could someone read each changed module top to bottom and follow it without jumping files?
3. Did the checks from "Goal-driven" pass? Run them again.
