"""
Correlation ID middleware — injects X-Request-ID into request state and response headers.
"""
from __future__ import annotations

import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a correlation ID for structured logging."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response
