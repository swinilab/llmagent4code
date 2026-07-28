"""Database migrations – creates tables and sets WAL mode.

Executed via `python -m app.db.migrations`.
"""

import asyncio
import os
from app.db.models import engine, Base

async def run_migrations():
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable WAL mode for durability and state preservation (NFR 2.3)
        await conn.execute("PRAGMA journal_mode=WAL")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migrations())
