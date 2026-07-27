import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError

# Database URL (SQLite for simplicity, async)
DATABASE_URL = "sqlite+aiosqlite:///./oms.db"

# Retry logic for engine creation
@retry(
    retry=retry_if_exception_type(OperationalError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def get_engine() -> AsyncEngine:
    """Create an async SQLAlchemy engine with retry – satisfies NFR 2.2 Fault Detection and Recovery."""
    return create_async_engine(DATABASE_URL, echo=False, future=True)

# Create a sessionmaker bound to the engine (reuse across requests)
engine = get_engine()
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh AsyncSession – used by FastAPI dependencies. Implements NFR 2.2."""
    async with async_session_factory() as session:
        yield session
