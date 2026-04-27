# Core Interfaces Module

This module defines the foundational abstractions for the Token Tracker system, ensuring adherence to **SOLID principles**, specifically the **Dependency Inversion Principle** and **Open/Closed Principle**.

## Components

1. **`ITokenizer`**: Strategy interface for implementing model-specific token counters (e.g., `tiktoken` for OpenAI).
2. **`IProviderPricing`**: Interface to calculate cost given token counts, making it easy to add new provider pricing models without changing existing code.
3. **`ITrackerStorage`**: Abstract repository for saving usage data, allowing us to swap Supabase/PostgreSQL for other storage mechanisms if needed.
4. **`ISecretManager`**: Interface for securely fetching sensitive credentials (like API keys) at runtime.
