from uuid import UUID

from app.core.errors import BadRequestError
from app.domain.validators import parse_uuid4


def parse_identifier(raw_identifier: str) -> UUID:
    try:
        return parse_uuid4(raw_identifier)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc


def missing_identifier() -> None:
    raise BadRequestError("A UUIDv4 resource identifier is required")

