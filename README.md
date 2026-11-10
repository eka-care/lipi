# Lipi

An open-source agentic scribe. Lipi listens to a meeting and turns it into structured notes, in any domain, on your own infrastructure.

> **Coming soon.** Code, setup docs and deployment guides are on the way.

## Stack

- **Speech:** [Parrotlet](https://huggingface.co/ekacare) ASR, built for Indian English, Hindi, Marathi, Kannada, Telugu and code-mixed speech
- **Agent:** [Echo SDK](https://github.com/eka-care/echo-sdk), model-agnostic agentic workflow
- **Protocol:** reference implementation of the [Scribe Exchange Protocol](https://github.com/eka-care/scribeexchangeprotocol)
- **Notes:** open-source LLMs with custom templates (minutes, action items, any format) and knowledge-base grounding
- **Ops:** self-hostable, OIDC sign-in, built for low bandwidth and flaky networks

## License

[Apache 2.0](LICENSE)
