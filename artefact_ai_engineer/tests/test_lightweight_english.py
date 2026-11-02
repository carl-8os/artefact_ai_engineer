from pathlib import Path
from music_store.infrastructure.ollama_model import OllamaLocalModel
from music_store.presentation.web import STATIC


def test_lightweight_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert OllamaLocalModel().model == "qwen2.5:1.5b"


def test_customer_facing_brand_is_english():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "Emporio Music Store" in html
    assert "Empório da Música" not in html


def test_local_inference_budget_is_bounded(monkeypatch):
    import json
    import music_store.infrastructure.ollama_model as module
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, *args): return b'{"choices":[{"message":{"role":"assistant","content":"Hello"}}]}'
    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data))
        return Response()
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    assert OllamaLocalModel().complete([{"role":"user","content":"Hello"}], [])["content"] == "Hello"
    assert captured["options"]["num_ctx"] <= 2048
    assert captured["options"]["num_predict"] <= 320
