"""OpenAI-compatible chat completions using Python standard library."""
import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError

class ModelError(RuntimeError):
    pass

class OpenAICompatibleModel:
    def __init__(self, *, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        parts = urlsplit(self.base_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("Valid HTTPS API endpoint required")

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        payload = json.dumps({"model":self.model,"messages":messages,"tools":tools,"tool_choice":"auto","temperature":0}).encode()
        req = Request(self.base_url + "/chat/completions", data=payload, headers={"Authorization":"Bearer " + self.api_key,"Content-Type":"application/json"}, method="POST")
        try:
            with urlopen(req, timeout=35) as resp:
                result = json.load(resp)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ModelError("LLM provider request failed") from exc
        try:
            return result["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("Invalid LLM provider response") from exc
