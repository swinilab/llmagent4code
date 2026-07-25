"""
Write-Ahead Log for state preservation and recovery
Implements state resynchronization tactic for fault recovery.
"""
import json
import sqlite3
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path


class WriteAheadLog:
    """
    Write-Ahead Log for persisting operations before execution.
    Enables state recovery after process crash.
    """
    
    def __init__(self, db_path: str = "./oms_wal.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS wal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    executed_at TEXT
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            self._conn.commit()
        return self._conn
    
    async def log_operation(
        self,
        operation: str,
        entity_type: str,
        entity_id: str,
        payload: Dict[str, Any],
    ) -> int:
        """Log an operation to WAL before execution"""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO wal_entries (operation, entity_type, entity_id, payload, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (operation, entity_type, entity_id, json.dumps(payload), datetime.utcnow().isoformat()),
            )
            conn.commit()
            return cursor.lastrowid
    
    async def mark_executed(self, entry_id: int):
        """Mark a WAL entry as executed"""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE wal_entries SET status = 'executed', executed_at = ? WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), entry_id),
            )
            conn.commit()
    
    async def get_pending_operations(self) -> List[Dict[str, Any]]:
        """Get all pending operations for recovery"""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, operation, entity_type, entity_id, payload, created_at
                FROM wal_entries
                WHERE status = 'pending'
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "operation": row[1],
                    "entity_type": row[2],
                    "entity_id": row[3],
                    "payload": json.loads(row[4]),
                    "created_at": row[5],
                }
                for row in rows
            ]
    
    async def save_state_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        state: Dict[str, Any],
    ):
        """Save a state snapshot for recovery"""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO state_snapshots (entity_type, entity_id, state, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (entity_type, entity_id, json.dumps(state), datetime.utcnow().isoformat()),
            )
            conn.commit()
    
    async def get_latest_snapshot(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get latest state snapshot for an entity"""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT state, created_at
                FROM state_snapshots
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (entity_type, entity_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "state": json.loads(row[0]),
                    "created_at": row[1],
                }
            return None
    
    async def clear_executed(self, older_than_seconds: int = 3600):
        """Clear executed entries older than specified seconds"""
        async with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cutoff = (datetime.utcnow().timestamp() - older_than_seconds)
            cursor.execute(
                """
                DELETE FROM wal_entries
                WHERE status = 'executed' AND executed_at < ?
                """,
                (datetime.fromtimestamp(cutoff).isoformat(),),
            )
            conn.commit()
    
    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None


# Global instance
_wal: Optional[WriteAheadLog] = None


def get_wal() -> WriteAheadLog:
    """Get or create global WAL instance"""
    global _wal
    if _wal is None:
        _wal = WriteAheadLog()
    return _wal
