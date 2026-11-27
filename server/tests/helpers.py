import json
import os
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS = Path(
    os.environ.get("LIPI_PROTOCOL_SCHEMAS", Path(__file__).resolve().parents[3] / "scribeexchangeprotocol" / "schemas")
)

SCHEMAS_BY_NAME = {
    path.name.removesuffix(".schema.json"): json.loads(path.read_text()) for path in SCHEMAS.glob("*.schema.json")
}
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS_BY_NAME.values()
)


def assert_matches(response: httpx.Response, name: str) -> None:
    """Validate a response body against a protocol schema, e.g. "04-discovery"."""
    validator = Draft202012Validator(
        SCHEMAS_BY_NAME[name], registry=REGISTRY, format_checker=Draft202012Validator.FORMAT_CHECKER
    )
    validator.validate(response.json())
