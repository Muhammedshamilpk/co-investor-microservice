"""
Domain-specific exceptions with HTTP status codes.
Register handlers in main.py via app.add_exception_handler().
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class ValuraBaseError(Exception):
    """Base error for all application exceptions."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class SafetyViolationError(ValuraBaseError):
    status_code = 400
    error_code = "SAFETY_VIOLATION"


class IntentClassificationError(ValuraBaseError):
    status_code = 422
    error_code = "INTENT_CLASSIFICATION_FAILED"


class AgentNotFoundError(ValuraBaseError):
    status_code = 404
    error_code = "AGENT_NOT_FOUND"


class LLMError(ValuraBaseError):
    status_code = 502
    error_code = "LLM_ERROR"


class LLMTimeoutError(LLMError):
    error_code = "LLM_TIMEOUT"


# ── FastAPI exception handlers ────────────────────────────────────────────────

async def valura_exception_handler(request: Request, exc: ValuraBaseError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )
