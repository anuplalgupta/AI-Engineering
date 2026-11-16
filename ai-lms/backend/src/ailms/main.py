"""The web application: one FastAPI app, every route under /api."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from ailms import system_routes
from ailms.catalog.api import router as catalog_router
from ailms.content.api import router as content_router
from ailms.identity.api import router as identity_router
from ailms.platform import queue
from ailms.platform.settings import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # The queue keeps one small connection pool open for putting jobs on it.
    queue.app.open()
    try:
        yield
    finally:
        queue.app.close()


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-LMS API",
        version=get_settings().app_version,
        openapi_url="/api/openapi.json",
        # The interactive pages load scripts from the internet; not wanted here.
        docs_url=None,
        redoc_url=None,
        lifespan=_lifespan,
        generate_unique_id_function=_operation_id,
    )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        # Every error has the same shape: {"detail": "one sentence"}.
        parts = []
        for item in error.errors():
            where = ".".join(str(p) for p in item["loc"] if p not in ("body", "query", "path"))
            parts.append(f"{where}: {item['msg']}" if where else item["msg"])
        return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request."})

    for router in (system_routes.router, identity_router, catalog_router, content_router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
