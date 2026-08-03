"""Direct PostgreSQL observation, bypassing the application entirely.

This module is the backbone of the study's independence claim. Every number an
application reports about itself could in principle be fabricated; what it
cannot fabricate is the state of the database sitting behind it. Three things
are read here that no amount of application-side dishonesty can fake:

  * how many scans the product table actually served  (ASR-P1, ASR-A2)
  * what the persisted workflow state really is       (ASR-A4)
  * a direct row mutation the application never sees  (ASR-P1)

The evaluator connects to PostgreSQL on its published host port, NOT through
Toxiproxy -- so it keeps observing even while the application's own database
path is severed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


class SchemaDiscoveryError(RuntimeError):
    """Raised when the generated schema cannot be interpreted.

    Table and column naming is left to the agent, so discovery is best-effort.
    A failure here is NOT_EXERCISABLE for the scenarios that need it.
    """


@dataclass(frozen=True)
class ScanCounts:
    """Sequential + index scans, summed."""

    total: int

    def delta(self, earlier: "ScanCounts") -> int:
        return self.total - earlier.total


class PgProbe:
    def __init__(self, dsn: str):
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=5)

    # ── schema discovery ──────────────────────────────────────────────────

    def find_product_table(self) -> str:
        """Locate the product table without assuming what the agent named it.

        Identified structurally rather than by name: the product table is the
        one carrying a description alongside a currency, which distinguishes it
        from every other entity in the domain model. Falls back to name
        matching only if the structural probe finds nothing.
        """
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, array_agg(column_name::text) AS cols
                FROM information_schema.columns
                WHERE table_schema = 'public'
                GROUP BY table_name
                """
            )
            tables = {r["table_name"]: {c.lower() for c in r["cols"]} for r in cur.fetchall()}

        structural = [
            name
            for name, cols in tables.items()
            if any("description" in c for c in cols) and any("currency" in c for c in cols)
        ]
        if len(structural) == 1:
            return structural[0]
        if len(structural) > 1:
            # Prefer the one whose name looks like a product table.
            named = [t for t in structural if "product" in t.lower()]
            if len(named) == 1:
                return named[0]

        by_name = [t for t in tables if t.lower() in ("products", "product", "oms_products")]
        if len(by_name) == 1:
            return by_name[0]

        raise SchemaDiscoveryError(
            f"cannot identify the product table; candidates={structural or list(tables)}"
        )

    # ── scan counting (external DB-read evidence) ─────────────────────────

    def wait_for_stats(self, timeout_s: float = 2.0) -> None:
        """Give PostgreSQL's statistics collector time to catch up.

        pg_stat_user_tables is updated asynchronously: a backend reports its
        activity when the transaction ends, and the collector applies it a
        moment later. Reading immediately after a request therefore tends to
        return the pre-request numbers, so a scan delta measured that way comes
        out as zero even though the query certainly ran.

        pg_stat_clear_snapshot only discards this session's cached view, which
        is necessary but not sufficient -- hence the short settle first.
        """
        import time as _time

        _time.sleep(min(timeout_s, 0.5))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_stat_clear_snapshot()")

    def scan_counts(self, table: str | None = None) -> ScanCounts:
        """Read cumulative scan counters for the product table.

        pg_stat_user_tables is always present, unlike pg_stat_statements which
        needs shared_preload_libraries the agent may not have configured, so we
        depend only on what a stock postgres:16 provides.

        Important limitation, established by measurement rather than assumed: a
        single-row lookup by primary key increments neither seq_scan nor
        idx_scan. PostgreSQL does not count a plain PK fetch as a scan at all.
        These counters are therefore meaningful for workloads that read many
        rows -- the throughput phase of ASR-P1 -- and are *not* a reliable way
        to prove that one specific read did or did not reach the database.

        Scenarios that need the latter must say so as a bound rather than an
        equality: a nonzero delta proves the database was reached, but a zero
        delta does not prove it was not.
        """
        with self._connect() as conn, conn.cursor() as cur:
            if table:
                cur.execute(
                    """
                    SELECT COALESCE(seq_scan, 0) + COALESCE(idx_scan, 0) AS total
                    FROM pg_stat_user_tables WHERE relname = %s
                    """,
                    (table,),
                )
                row = cur.fetchone()
                return ScanCounts(total=int(row["total"]) if row else 0)

            cur.execute(
                """
                SELECT COALESCE(SUM(COALESCE(seq_scan, 0) + COALESCE(idx_scan, 0)), 0) AS total
                FROM pg_stat_user_tables
                """
            )
            return ScanCounts(total=int(cur.fetchone()["total"]))

    # ── direct mutation (cache-staleness evidence) ────────────────────────

    def set_product_description(self, table: str, product_id: str, description: str) -> None:
        """Change a product row behind the application's back.

        This is what makes ASR-P1 a real cache test: the application is given no
        opportunity to invalidate, so serving the old value proves a maintained
        copy exists, and serving the new one after TTL proves it expires.
        """
        with self._connect() as conn, conn.cursor() as cur:
            col = self._description_column(cur, table)
            cur.execute(
                f'UPDATE {_ident(table)} SET {_ident(col)} = %s WHERE id::text = %s',
                (description, product_id),
            )
            if cur.rowcount != 1:
                raise SchemaDiscoveryError(
                    f"expected to update exactly 1 product row, updated {cur.rowcount}"
                )
            conn.commit()

    @staticmethod
    def _description_column(cur: psycopg.Cursor, table: str) -> str:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
              AND column_name ILIKE '%%description%%'
            """,
            (table,),
        )
        rows = cur.fetchall()
        if len(rows) != 1:
            raise SchemaDiscoveryError(
                f"cannot identify description column on {table!r}: {[r['column_name'] for r in rows]}"
            )
        return rows[0]["column_name"]

    # ── persisted workflow state (transaction evidence) ───────────────────

    def entity_status(self, table: str, entity_id: str) -> str | None:
        """Read a status column straight from durable storage.

        ASR-A4 asks whether a rollback really happened. Asking the application
        would let a cache or an in-memory shadow answer for it; asking
        PostgreSQL cannot be fooled that way.
        """
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'SELECT status FROM {_ident(table)} WHERE id::text = %s',
                (entity_id,),
            )
            row = cur.fetchone()
            return None if row is None else str(row["status"])

    def find_table(self, *name_candidates: str) -> str:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            existing = {r["table_name"].lower(): r["table_name"] for r in cur.fetchall()}
        for candidate in name_candidates:
            if candidate.lower() in existing:
                return existing[candidate.lower()]
        raise SchemaDiscoveryError(f"none of {name_candidates} exist; have {sorted(existing)}")

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def _ident(name: str) -> str:
    """Quote an identifier discovered at runtime.

    These names come from information_schema rather than from user input, but
    they are still interpolated into SQL, so they get quoted properly.
    """
    if not name.replace("_", "").isalnum():
        raise SchemaDiscoveryError(f"refusing to interpolate suspicious identifier {name!r}")
    return '"' + name.replace('"', '""') + '"'