"""Verify offline-first selection and local-only Ollama integration."""
import io
import json
from unittest.mock import patch
import pytest
from music_store.infrastructure.model_factory import create_model
from music_store.infrastructure.ollama_model import OllamaLocalModel
from music_store.infrastructure.openai_model import ModelError


def test_local_default_requires_no_api_key(monkeypatch):
    monkeypatch.delenv('LLM_PROVIDER', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert isinstance(create_model(), OllamaLocalModel)


def test_explicit_local_provider(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    monkeypatch.setenv('OLLAMA_MODEL', 'qwen2.5:3b')
    assert create_model().model == 'qwen2.5:3b'


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'unknown')
    with pytest.raises(ValueError, match='LLM_PROVIDER'):
        create_model()


def test_local_endpoint_only():
    model = OllamaLocalModel()
    assert model.endpoint == 'http://127.0.0.1:11434/v1/chat/completions'


def test_completion_tool_call_roundtrip():
    model = OllamaLocalModel()
    expected = {'role': 'assistant', 'content': '', 'tool_calls': [{'id':'1','type':'function','function':{'name':'search_catalog','arguments':'{}'}}]}
    class Response(io.BytesIO):
        pass
    def fake_urlopen(request, timeout):
        assert request.full_url.startswith('http://127.0.0.1:11434/')
        assert json.loads(request.data)['tools'] == [{'type': 'function'}]
        return Response(json.dumps({'choices':[{'message':expected}]}).encode())
    with patch('music_store.infrastructure.ollama_model.urlopen', side_effect=fake_urlopen):
        assert model.complete([{'role':'user','content':'guitar'}], [{'type':'function'}]) == expected


def test_unavailable_ollama_has_actionable_error():
    from urllib.error import URLError
    with patch('music_store.infrastructure.ollama_model.urlopen', side_effect=URLError('offline')):
        with pytest.raises(ModelError, match='Start Ollama'):
            OllamaLocalModel().complete([], [])
