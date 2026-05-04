"""Sync orchestrator: pulls daily usage from each provider and upserts to DB."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, timedelta

from src.storage.database import PostgresStorage
from src.usage_puller.interfaces import IUsagePuller
from src.usage_puller.openai_puller import OpenAIUsagePuller
from src.usage_puller.anthropic_puller import AnthropicUsagePuller
from src.usage_puller.gemini_puller import GeminiUsagePuller

log = logging.getLogger(__name__)


def build_pullers() -> list[IUsagePuller]:
    """Construct pullers for every provider with credentials available.

    A missing admin key for one provider should not break the others.
    """
    pullers: list[IUsagePuller] = []
    if os.environ.get("OPENAI_ADMIN_KEY"):
        pullers.append(OpenAIUsagePuller())
    if os.environ.get("ANTHROPIC_ADMIN_KEY"):
        pullers.append(AnthropicUsagePuller())
    pullers.append(GeminiUsagePuller())  # stub, no key needed
    return pullers


async def sync(
    start: date,
    end: date,
    storage: PostgresStorage | None = None,
    pullers: list[IUsagePuller] | None = None,
) -> dict:
    """Pull usage from every configured provider for [start, end] and upsert.

    Returns a per-provider summary suitable for logging or an HTTP response.
    """
    storage = storage or PostgresStorage()
    pullers = pullers if pullers is not None else build_pullers()

    summary: dict = {}
    for puller in pullers:
        try:
            rows = await puller.pull_daily(start, end)
        except Exception as e:
            log.exception("Pull failed for %s", puller.provider)
            summary[puller.provider] = {"error": str(e), "rows": 0}
            continue

        for r in rows:
            await storage.upsert_daily_usage(
                day=r.date,
                provider=r.provider,
                model=r.model,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cost_usd=r.cost_usd,
            )
        summary[puller.provider] = {"rows": len(rows)}
    return summary


def cli() -> None:
    """`python -m src.usage_puller.sync [days]` — defaults to last 7 days."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    end = date.today()
    start = end - timedelta(days=days - 1)

    async def _run():
        storage = PostgresStorage()
        await storage.init_db()
        result = await sync(start, end, storage=storage)
        print(f"Synced {start} → {end}: {result}")
        await storage.engine.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
