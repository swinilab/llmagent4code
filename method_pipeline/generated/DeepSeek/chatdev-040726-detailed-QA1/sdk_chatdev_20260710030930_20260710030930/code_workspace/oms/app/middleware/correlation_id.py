"""Correlation ID middleware for request tracing.

Adds a unique correlation ID to each request, accessible via:
  - Request header (X-Correlation-ID)
  - Structured log entries
  - Response header
"""

import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a correlation ID into every request/response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER, str(uuid.uuid4()))
        # Store in request state for access in handlers/logging
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
