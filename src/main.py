"""
FastAPI application factory and lifecycle events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.routes import query
from src.core.config import get_settings
from src.core.exceptions import ValuraBaseError, valura_exception_handler
from src.core.logging import configure_logging, get_logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging(debug=settings.DEBUG)
    log = get_logger("src.startup")
    log.info("starting_valura_api", version=settings.APP_VERSION, env=settings.ENVIRONMENT)
    yield
    # Shutdown
    log.info("shutting_down_valura_api")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(ValuraBaseError, valura_exception_handler)

    # Routes
    app.include_router(query.router, prefix="/api/v1")

    @app.get("/health", tags=["System"])
    def health_check() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
