"""Local Ollama adapter using its OpenAI-compatible chat completions endpoint."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from music_store.infrastructure.openai_model import ModelError


class OllamaLocalModel:
    local_fast_facts = True
    """Connect exclusively to Ollama on loopback; no cloud key or external API."""

    def __init__(self, model: str | None = None, port: int = 11434):
        self.model = model or os.environ.get('OLLAMA_MODEL', 'qwen2.5:1.5b')
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError('Invalid local Ollama port')
        self.endpoint = f'http://127.0.0.1:{port}/v1/chat/completions'

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        payload = json.dumps({
            'model': self.model,
            'messages': messages,
            'tools': tools,
            'tool_choice': 'auto',
            'temperature': 0,
            'stream': False,
            'options': {'num_ctx': 2048, 'num_predict': 320, 'num_thread': max(1, min(8, os.cpu_count() or 4))},
            'keep_alive': '10m',
        }).encode('utf-8')
        request = Request(self.endpoint, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=180) as response:
                result = json.load(response)
        except HTTPError as exc:
            if exc.code == 404:
                raise ModelError(f'Local model {self.model!r} not found. Run: ollama pull {self.model}') from exc
            raise ModelError(f'Local Ollama request failed (HTTP {exc.code})') from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ModelError('Cannot connect to local Ollama. Start Ollama and verify it is running.') from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise ModelError('Invalid JSON from local Ollama') from exc
        try:
            message = result['choices'][0]['message']
            if not isinstance(message, dict):
                raise TypeError('Message must be an object')
            return message
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError('Invalid chat completion response from local Ollama') from exc
