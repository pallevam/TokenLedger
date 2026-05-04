"""Gemini / Google AI usage puller (stub).

Google does not expose a first-party "usage report" endpoint for the
Gemini API the way OpenAI and Anthropic do. Two viable sources:

  1. Cloud Billing — `cloudbilling.googleapis.com` / BigQuery billing export.
     Filter to service `generativelanguage.googleapis.com`. This gives cost
     per day but not token counts.

  2. Cloud Monitoring — metrics under
     `generativelanguage.googleapis.com/...` expose request counts;
     token-level metrics are limited.

The cleanest path is enabling BigQuery billing export and querying it.
This puller is a placeholder so the orchestrator can run end-to-end; it
returns an empty list and logs a warning until you wire one of the above.
"""
from __future__ import annotations

import logging
from datetime import date

from src.usage_puller.interfaces import IUsagePuller, DailyUsage

log = logging.getLogger(__name__)


class GeminiUsagePuller(IUsagePuller):
    provider = "gemini"

    async def pull_daily(self, start: date, end: date) -> list[DailyUsage]:
        log.warning(
            "GeminiUsagePuller is a stub. Wire it to BigQuery billing export "
            "or Cloud Monitoring to get real numbers."
        )
        return []
