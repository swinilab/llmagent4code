"""Domain error taxonomy.

The three-step FK validation from Implementation note 2 maps onto these:
  (a) malformed reference   -> ValidationError        -> 400
  (b) valid but not found   -> NotFoundError          -> 404
  (c) wrong workflow state  -> ConflictError          -> 409

Infrastructure conditions add:
  RateLimitExceeded         -> 429   (NFR 1.1)
  DependencyUnavailable     -> 503   (NFR 2.1 / 2.2)
"""


class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class ValidationError(DomainError):
    status_code = 400
    code = "validation_error"


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class RateLimitExceeded(DomainError):
    status_code = 429
    code = "rate_limited"


class DependencyUnavailable(DomainError):
    status_code = 503
    code = "dependency_unavailable"
