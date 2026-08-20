from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


ERROR_CONTENT: dict[str, Any] = {
    "application/json": {
        "schema": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "requestId": {"type": ["string", "null"]},
                        "details": {},
                    },
                }
            },
            "required": ["error"],
        }
    }
}


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        for path, path_item in schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                responses = operation.setdefault("responses", {})
                if responses.pop("422", None) is not None:
                    responses.setdefault(
                        "400",
                        {"description": "Malformed identifier or request validation failure", "content": ERROR_CONTENT},
                    )
                if path.startswith("/api/v1/") and "{" in path:
                    responses.setdefault(
                        "404",
                        {"description": "A well-formed referenced resource was not found", "content": ERROR_CONTENT},
                    )
                if (
                    path.startswith("/api/v1/orders/")
                    or path.startswith("/api/v1/payments/")
                    or path in {"/api/v1/orders", "/api/v1/invoices", "/api/v1/payments"}
                ):
                    responses.setdefault(
                        "409",
                        {"description": "The requested workflow transition conflicts with current state", "content": ERROR_CONTENT},
                    )
                if path in {"/api/v1/orders", "/api/v1/invoices", "/api/v1/payments"}:
                    responses.setdefault(
                        "404",
                        {"description": "A well-formed referenced resource was not found", "content": ERROR_CONTENT},
                    )
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
