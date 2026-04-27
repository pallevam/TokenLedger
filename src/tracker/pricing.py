from src.core.interfaces import IProviderPricing

class SimplePricing(IProviderPricing):
    # Cost per 1M tokens
    PRICING = {
        "gpt-4": {"prompt": 30.0, "completion": 60.0},
        "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
        "claude-3-opus-20240229": {"prompt": 15.0, "completion": 75.0},
        "claude-3-sonnet-20240229": {"prompt": 3.0, "completion": 15.0},
        "gemini-1.5-pro": {"prompt": 7.0, "completion": 21.0}
    }

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        rates = self.PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
        prompt_cost = (prompt_tokens / 1_000_000) * rates["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * rates["completion"]
        return prompt_cost + completion_cost
