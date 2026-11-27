import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from lipi.api import discovery, sessions
from lipi.core import config, db, errors

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("lipi")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.state.config = config.load()
    await db.connect(app.state.config.database_url)
    yield
    await db.close()


app = FastAPI(title="Lipi", lifespan=lifespan)
app.add_exception_handler(errors.LipiError, errors.render)
app.add_exception_handler(RequestValidationError, errors.invalid)
app.add_exception_handler(StarletteHTTPException, errors.no_route)
app.add_exception_handler(Exception, errors.internal)
app.include_router(discovery.router)
app.include_router(sessions.router)


@app.middleware("http")
async def log_request(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    started = time.perf_counter()
    # An unhandled error skips the return below; it is rendered as 500 by errors.internal, so log it as 500.
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000)
        log.info(
            "request method=%s path=%s status=%s duration_ms=%s", request.method, request.url.path, status, duration_ms
        )
