from google.cloud import secretmanager
from src.core.interfaces import ISecretManager
import functools
import os

class GCPSecretManager(ISecretManager):
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("Google Cloud Project ID is required.")
        self.client = secretmanager.SecretManagerServiceClient()

    @functools.lru_cache(maxsize=10)
    def get_api_key(self, provider: str) -> str:
        """
        Securely fetches the API key from GCP Secret Manager.
        The secrets are expected to be named '{provider}_api_key' 
        (e.g., 'openai_api_key', 'anthropic_api_key').
        Results are cached in-memory to reduce latency and costs.
        """
        secret_id = f"{provider.lower()}_api_key"
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
        
        try:
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch secret for {provider}: {str(e)}")

# Fallback for local development
class EnvVarSecretManager(ISecretManager):
    def get_api_key(self, provider: str) -> str:
        key_name = f"{provider.upper()}_API_KEY"
        key = os.environ.get(key_name)
        if not key:
            raise ValueError(f"Environment variable {key_name} not found.")
        return key
