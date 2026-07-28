import json
import os
import asyncio
import aiofiles

WAL_PATH = "./data/wal.log"

class WAL:
    def __init__(self):
        os.makedirs(os.path.dirname(WAL_PATH), exist_ok=True)
        self._lock = asyncio.Lock()

    async def append_to_wal(self, entry: dict):
        async with self._lock:
            async with aiofiles.open(WAL_PATH, mode="a") as f:
                await f.write(json.dumps(entry) + "\n")

    async def replay_wal_on_startup(self):
        if not os.path.exists(WAL_PATH):
            return
        async with aiofiles.open(WAL_PATH, mode="r") as f:
            async for line in f:
                entry = json.loads(line)
                # Simple dispatcher – in a real system each action would trigger the appropriate service.
                # For this demo we just log the replay.
                print(f"Replaying WAL entry: {entry}")
        # Truncate after successful replay
        open(WAL_PATH, "w").close()
