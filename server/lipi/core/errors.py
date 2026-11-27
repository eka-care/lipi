import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("lipi")


class LipiError(Exception):
    """Every refusal. `code` comes from protocol §11.3 only."""

    def __init__(self, code: str, status: int, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message
        self.details = details


def _body(code: str, message: str, details: dict | None) -> dict:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def render(request: Request, exc: LipiError) -> JSONResponse:
    return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status)


async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    if first["type"] == "json_invalid":
        return JSONResponse(_body("invalid_request", "The request body is not valid JSON.", None), status_code=400)
    field = ".".join(str(part) for part in first["loc"] if part != "body")
    message = f"{field}: {first['msg']}." if field else f"{first['msg']}."
    return JSONResponse(_body("invalid_request", message, None), status_code=400)


async def no_route(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # decision 19: unknown route and wrong method are a malformed request (§11.3 pairs invalid_request with 400)
    message = f"There is no {request.method} {request.url.path} endpoint."
    return JSONResponse(_body("invalid_request", message, None), status_code=400)


async def internal(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error method=%s path=%s", request.method, request.url.path)
    return JSONResponse(_body("internal_error", "The service failed. Try again later.", None), status_code=500)
