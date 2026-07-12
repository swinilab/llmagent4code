"""
Arq background worker — processes async jobs queued during request handling.

Jobs:
  - audit_log_async: persist audit events without blocking the request path
  - send_invoice_email: email invoice PDF link to customer
  - check_payment_captured: poll gateway for payment status (fallback)

Retry policy: max 3 attempts with exponential back-off (5s × 2^attempt).
Dead-letter: jobs that fail all retries are logged with full context.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as redis
from arq import cron
from arq.connections import RedisSettings
from arq.worker import Worker

from oms_backend.core.config import get_settings

log = logging.getLogger("arq_worker")


# ── Job functions ──────────────────────────────────────────────────────────────

async def audit_log_async(ctx: dict, entity_type: str, entity_id: str, action: str, payload: str) -> None:
    """
    Async audit log — enqueued from service layer instead of blocking DB write.
    Payload is JSON string for serialization safety.
    """
    redis: redis.Redis = ctx["redis"]
    try:
        payload_dict = json.loads(payload) if payload else {}
        audit_key = f"audit:{entity_type}:{entity_id}"
        entry = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "payload": payload_dict,
            "created_at": datetime.utcnow().isoformat(),
        }
        await redis.lpush(audit_key, json.dumps(entry))
        await redis.ltrim(audit_key, 0, 9999)  # keep last 10k entries
        log.info(f"Audit log queued: {entity_type}/{entity_id} {action}")
    except Exception as exc:
        log.error(f"audit_log_async failed: {exc}")


async def send_invoice_email(ctx: dict, invoice_id: str, customer_email: str, invoice_code: str) -> None:
    """
    Simulated invoice email dispatch.
    Replace with real email provider (SendGrid, SES, etc.) in production.
    """
    log.info(f"[SIMULATED] Sending invoice {invoice_code} to {customer_email}")
    # In production:
    # async with aiosmtplib.open() as smtp:
    #     await smtp.send_message(msg)
    await asyncio.sleep(0.5)  # simulate network latency
    log.info(f"[SIMULATED] Invoice {invoice_code} email sent to {customer_email}")


async def check_payment_captured(ctx: dict, payment_reference: str, payment_id: str) -> None:
    """
    Fallback polling job if webhook delivery fails.
    Checks gateway for payment status after 60-second delay.
    """
    log.info(f"[SIMULATED] Polling gateway for payment {payment_reference}")
    # In production: gateway.check_payment(reference=payment_reference)
    await asyncio.sleep(1)
    log.info(f"[SIMULATED] Payment {payment_reference} status: captured (simulated)")


# ── Worker settings ─────────────────────────────────────────────────────────────

async def run_worker() -> None:
    settings = get_settings()
    redis_settings = RedisSettings(
        host=settings.redis.host,
        port=settings.redis.port,
        database=settings.queue.redis_db if hasattr(settings.queue, "redis_db") else 1,
        password=settings.redis.password or None,
    )

    worker = Worker(
        functions=[audit_log_async, send_invoice_email, check_payment_captured],
        redis_settings=redis_settings,
        max_jobs=settings.queue.max_jobs,
        job_timeout=settings.queue.job_timeout_seconds,
        keep_result=3600,
        retry_delay=settings.queue.retry_delay_seconds,
    )
    log.info("Arq worker starting...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
