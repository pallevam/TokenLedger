# Security Module

This module handles the secure retrieval and caching of sensitive credentials, primarily API keys for various LLM providers.

## Key Design Decisions
- **No Hardcoded Secrets**: Credentials must never exist in the codebase or plain text environment variables.
- **GCP Secret Manager Integration**: We utilize `google-cloud-secret-manager` to fetch API keys dynamically at runtime.
- **Caching**: To reduce API latency and GCP costs, secrets are cached in memory for a short duration using `functools.lru_cache` or a custom TTL cache.
