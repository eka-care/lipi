# Lipi — rules for build sessions

Read `docs/design.md`, then your phase in `docs/phases.md`, then the protocol chapters it names.

- The Scribe Exchange Protocol repository (`../scribeexchangeprotocol`, attached to the session) is the contract. Never invent or rename a shape, status or code. If it must change, stop and say so.
- Plan, show the plan, wait for an explicit go. Then build.
- Ask; never assume. A gap in the docs is a question, not a guess.
- Build the current phase only.
- Follow the skills `lipi-code-style` and `lipi-testing`.
- Record decisions in `docs/design.md` §8, next number, never renumber.
- `vaarta-bharatAI` is reference only. Copy nothing; do not model Lipi on it.
- Nothing Eka-specific in this repository.
- Plain words in docs, comments and error messages.

Leaving a session: tests green · `design.md` and `phases.md` updated · `scripts/demo.sh` runs · a done / deferred / open note at the top of the phase in `phases.md`.
