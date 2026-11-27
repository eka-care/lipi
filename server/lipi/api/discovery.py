from fastapi import APIRouter, Request, Response

from lipi.core.config import Config

router = APIRouter()

# Required by the protocol §4 schema before Lipi has templates or documents (phases 4–5); decision 13.
TEMPLATES = {"max_instruction_chars": 20000, "max_per_caller": 50}
DOCUMENTS = {"max_content_bytes": 1048576}
OUTPUT_FORMATS = ["markdown"]
STRUCTURING_MODELS = [
    {"id": "none", "display_name": "No structuring model yet", "default": True}
]


def to_discovery(config: Config) -> dict:
    return {
        "protocol": "scribe-exchange",
        "protocol_version": "0.1",
        "supported_versions": ["0.1"],
        "deprecated_versions": [],
        "service": {"name": config.service_name},
        "endpoints": {"base_url": f"{config.base_url}/v1"},
        "auth": None,
        "capabilities": {
            "sources": {
                "max_per_session": config.max_sources_per_session,
                "kinds": {
                    "audio": {
                        "max": config.max_audio_sources,
                        "input": ["chunked", "file"],
                        "formats": config.audio_formats,
                        "max_chunk_seconds": config.max_chunk_seconds,
                        "max_seconds": config.max_seconds,
                        "inactivity_seconds": config.inactivity_seconds,
                    },
                },
            },
            "templates": TEMPLATES,
            "documents": DOCUMENTS,
            "output_formats": OUTPUT_FORMATS,
        },
        "models": {
            "stt": [
                {"id": model, "display_name": model, "default": index == 0}
                for index, model in enumerate(config.stt_models)
            ],
            "structuring": STRUCTURING_MODELS,
        },
        # auto_detection is a constant under decision 13
        "languages": {"supported": config.languages, "auto_detection": True},
        "profiles": [],
    }


@router.get("/.well-known/scribe-exchange")
async def discovery(request: Request, response: Response) -> dict:
    # protocol §4.1: SHOULD be cacheable, one hour recommended
    response.headers["Cache-Control"] = "max-age=3600"
    return to_discovery(request.app.state.config)
