"""Select a local-first LLM without changing application business rules."""
import os
from music_store.infrastructure.ollama_model import OllamaLocalModel
from music_store.infrastructure.openai_model import OpenAICompatibleModel


def create_model():
    provider = os.environ.get('LLM_PROVIDER', 'ollama').strip().lower()
    if provider == 'ollama':
        return OllamaLocalModel()
    if provider == 'openai':
        return OpenAICompatibleModel()
    raise ValueError('LLM_PROVIDER must be ollama or openai')
