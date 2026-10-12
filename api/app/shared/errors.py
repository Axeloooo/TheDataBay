"""Typed API errors and handlers for consistent JSON error responses."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard API error envelope."""

    error: str
    message: str
    details: dict[str, Any] | None = None


class ApiError(Exception):
    """Application error rendered as an ErrorResponse."""

    def __init__(
        self,
        *,
        status_code: int,
        error: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error=self.error,
            message=self.message,
            details=self.details,
        )


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Render ApiError instances as the shared error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().model_dump(),
    )
