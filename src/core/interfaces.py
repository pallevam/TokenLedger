from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class UsageRecord(BaseModel):
    user_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_cost: float
    latency_ms: Optional[int] = None

class ITokenizer(ABC):
    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Count the number of tokens in the given text for a specific model."""
        pass

class IProviderPricing(ABC):
    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calculate the estimated cost for a given number of tokens and model."""
        pass

class ITrackerStorage(ABC):
    @abstractmethod
    async def log_usage(self, record: UsageRecord) -> None:
        """Log a token usage record to the database."""
        pass

    @abstractmethod
    async def get_usage(self, user_id: str) -> Dict[str, Any]:
        """Retrieve aggregated usage statistics for a specific user."""
        pass

class ISecretManager(ABC):
    @abstractmethod
    def get_api_key(self, provider: str) -> str:
        """Securely fetch the API key for a specific LLM provider."""
        pass
