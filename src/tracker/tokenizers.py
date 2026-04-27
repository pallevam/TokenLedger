import tiktoken
from src.core.interfaces import ITokenizer

class TiktokenTokenizer(ITokenizer):
    def count_tokens(self, text: str, model: str) -> int:
        """
        Counts tokens using OpenAI's tiktoken library.
        Defaults to cl100k_base encoding if the model is not explicitly found.
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback for newer models or unrecognized variants
            encoding = tiktoken.get_encoding("cl100k_base")
            
        return len(encoding.encode(text))

# Placeholders for other providers
class AnthropicTokenizer(ITokenizer):
    def count_tokens(self, text: str, model: str) -> int:
        # In a real implementation, we might use the anthropic SDK's count_tokens
        # Here we do a rudimentary estimation or use cl100k_base as proxy
        return len(text.split()) # Highly naive fallback

class GeminiTokenizer(ITokenizer):
    def count_tokens(self, text: str, model: str) -> int:
        # Google's vertexai SDK has a count_tokens method
        # Naive fallback
        return len(text.split())
