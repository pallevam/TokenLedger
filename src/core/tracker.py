from typing import Dict, Any, Type
import time
from src.core.interfaces import ITokenizer, IProviderPricing, ITrackerStorage, ISecretManager, UsageRecord
from src.tracker.tokenizers import TiktokenTokenizer, AnthropicTokenizer, GeminiTokenizer
from src.tracker.pricing import SimplePricing
from src.storage.database import PostgresStorage
from src.security.gcp_secret_manager import GCPSecretManager, EnvVarSecretManager
import os

class TokenTracker:
    """
    Main orchestrator for tracking tokens, calculating costs, and securely fetching API keys.
    """
    def __init__(
        self,
        storage: ITrackerStorage = None,
        pricing: IProviderPricing = None,
        secret_manager: ISecretManager = None
    ):
        self.storage = storage or PostgresStorage()
        self.pricing = pricing or SimplePricing()
        
        # Use EnvVar for local dev if GCP Project is not set
        if secret_manager:
            self.secret_manager = secret_manager
        elif os.environ.get("GOOGLE_CLOUD_PROJECT"):
            self.secret_manager = GCPSecretManager()
        else:
            self.secret_manager = EnvVarSecretManager()

        self._tokenizers: Dict[str, ITokenizer] = {
            "openai": TiktokenTokenizer(),
            "anthropic": AnthropicTokenizer(),
            "gemini": GeminiTokenizer()
        }

    def get_api_key(self, provider: str) -> str:
        """Securely fetch the API key for the given provider."""
        return self.secret_manager.get_api_key(provider)

    def track_request(self, user_id: str, provider: str, model: str, prompt: str, response_text: str, latency_ms: int = None) -> UsageRecord:
        """
        Calculates tokens and costs for a given request and logs it to the database.
        """
        provider_key = provider.lower()
        tokenizer = self._tokenizers.get(provider_key)
        
        if not tokenizer:
            raise ValueError(f"No tokenizer found for provider: {provider}")

        # Count tokens
        prompt_tokens = tokenizer.count_tokens(prompt, model)
        completion_tokens = tokenizer.count_tokens(response_text, model)
        
        # Calculate cost
        total_cost = self.pricing.calculate_cost(prompt_tokens, completion_tokens, model)

        # Create record
        record = UsageRecord(
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=total_cost,
            latency_ms=latency_ms
        )

        # Log to storage
        self.storage.log_usage(record)
        return record
