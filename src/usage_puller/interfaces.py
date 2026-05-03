from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class DailyUsage:
    """One row of aggregated daily usage from a provider."""
    date: date
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class IUsagePuller(ABC):
    """Pulls historical daily usage from a provider's billing/usage API."""

    provider: str

    @abstractmethod
    async def pull_daily(self, start: date, end: date) -> list[DailyUsage]:
        """Return one DailyUsage per (date, model) in [start, end] inclusive."""
        ...
