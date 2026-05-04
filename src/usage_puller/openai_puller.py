"""OpenAI usage puller.

Uses the OpenAI Platform Usage API (admin scope). Requires an Admin API key
created at https://platform.openai.com/settings/organization/admin-keys
(NOT a regular sk-... project key).

Docs:
  - https://platform.openai.com/docs/api-reference/usage
  - GET /v1/organization/usage/completions   (token counts, bucketed)
  - GET /v1/organization/costs               (USD cost, bucketed daily)
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from collections import defaultdict

import httpx

from src.usage_puller.interfaces import IUsagePuller, DailyUsage


OPENAI_USAGE_URL = "https://api.openai.com/v1/organization/usage/completions"
OPENAI_COSTS_URL = "https://api.openai.com/v1/organization/costs"


def _to_unix(d: date, end_of_day: bool = False) -> int:
    t = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    return int(datetime.combine(d, t, tzinfo=timezone.utc).timestamp())


class OpenAIUsagePuller(IUsagePuller):
    provider = "openai"

    def __init__(self, admin_api_key: str | None = None):
        self.admin_api_key = admin_api_key or os.environ.get("OPENAI_ADMIN_KEY")
        if not self.admin_api_key:
            raise ValueError(
                "OPENAI_ADMIN_KEY is not set. Create an Admin key at "
                "https://platform.openai.com/settings/organization/admin-keys"
            )

    async def pull_daily(self, start: date, end: date) -> list[DailyUsage]:
        headers = {"Authorization": f"Bearer {self.admin_api_key}"}
        start_ts = _to_unix(start)
        end_ts = _to_unix(end, end_of_day=True)

        # Bucket by day, group by model so we can compute per-model rows.
        usage_params = {
            "start_time": start_ts,
            "end_time": end_ts,
            "bucket_width": "1d",
            "group_by": "model",
            "limit": 31,
        }
        cost_params = {
            "start_time": start_ts,
            "end_time": end_ts,
            "bucket_width": "1d",
            "limit": 31,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            tokens_by_day_model: dict[tuple[date, str], dict] = defaultdict(
                lambda: {"input": 0, "output": 0}
            )
            async for bucket in self._paginate(client, OPENAI_USAGE_URL, usage_params, headers):
                day = datetime.fromtimestamp(bucket["start_time"], tz=timezone.utc).date()
                for result in bucket.get("results", []):
                    model = result.get("model") or "unknown"
                    key = (day, model)
                    tokens_by_day_model[key]["input"] += result.get("input_tokens", 0)
                    tokens_by_day_model[key]["output"] += result.get("output_tokens", 0)

            # Costs are not broken down by model in the same bucket; pull daily totals
            # and apportion proportionally to that day's token volume per model.
            cost_by_day: dict[date, float] = defaultdict(float)
            async for bucket in self._paginate(client, OPENAI_COSTS_URL, cost_params, headers):
                day = datetime.fromtimestamp(bucket["start_time"], tz=timezone.utc).date()
                for result in bucket.get("results", []):
                    amount = result.get("amount", {}) or {}
                    cost_by_day[day] += float(amount.get("value", 0.0))

        # Apportion daily cost across models by total token share.
        day_totals: dict[date, int] = defaultdict(int)
        for (day, _model), counts in tokens_by_day_model.items():
            day_totals[day] += counts["input"] + counts["output"]

        rows: list[DailyUsage] = []
        for (day, model), counts in tokens_by_day_model.items():
            total = counts["input"] + counts["output"]
            day_total = day_totals[day]
            share = (total / day_total) if day_total else 0.0
            rows.append(
                DailyUsage(
                    date=day,
                    provider=self.provider,
                    model=model,
                    input_tokens=counts["input"],
                    output_tokens=counts["output"],
                    cost_usd=round(cost_by_day.get(day, 0.0) * share, 6),
                )
            )
        return rows

    async def _paginate(self, client: httpx.AsyncClient, url: str, params: dict, headers: dict):
        next_page: str | None = None
        while True:
            q = dict(params)
            if next_page:
                q["page"] = next_page
            resp = await client.get(url, params=q, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            for bucket in payload.get("data", []):
                yield bucket
            if not payload.get("has_more"):
                break
            next_page = payload.get("next_page")
            if not next_page:
                break
