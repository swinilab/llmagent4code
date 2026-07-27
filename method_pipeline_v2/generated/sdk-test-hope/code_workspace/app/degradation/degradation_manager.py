# Simple feature flag based degradation manager

# In a real system this could be driven by metrics; here we toggle via env var
import os

NON_ESSENTIAL_ENDPOINTS = {
    '/api/v1/customers': True,
    '/api/v1/products': True,
    # Add others as needed
}

def should_degrade_feature(path: str) -> bool:
    return NON_ESSENTIAL_ENDPOINTS.get(path, False) and os.getenv('DEGRADE', '0') == '1'

def disable_non_essential_endpoints(app) -> None:
    # Middleware to block non-essential when degrade flag is set
    @app.middleware('http')
    async def degradation_middleware(request, call_next):
        if should_degrade_feature(request.url.path):
            from fastapi import Response
            return Response(status_code=503, content='Service degraded')
        return await call_next(request)
