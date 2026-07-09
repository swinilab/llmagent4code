"""
Middleware that injects a correlation ID into the request scope and
logging context for end-to-end tracing.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Read or generate a correlation ID and make it available via
    ``request.state.correlation_id`` and the response header."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = cid

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = cid
        return response
