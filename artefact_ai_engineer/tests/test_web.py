"""Web interface tests using only Python standard library and mocked model."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from music_store.presentation.web import ChatSessions, make_handler, STATIC


class FakeAgent:
    def respond(self, message, history=None):
        return f'{len(history or [])}: {message}'


def test_sessions_isolated_and_followups():
    sessions = ChatSessions(FakeAgent())
    first_id, first = sessions.chat(None, 'olá')
    same_id, second = sessions.chat(first_id, 'e agora?')
    another_id, third = sessions.chat(None, 'olá')
    assert first == '0: olá'
    assert second == '2: e agora?'
    assert third == '0: olá'
    assert first_id == same_id and first_id != another_id
    assert len(first_id) > 32


def test_invalid_messages_rejected():
    sessions = ChatSessions(FakeAgent())
    for value in ('', '  ', 'x' * 4001, None, 10):
        with pytest.raises(ValueError):
            sessions.chat(None, value)


def test_web_endpoints_and_security():
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(ChatSessions(FakeAgent())))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base + '/') as response:
            html = response.read().decode()
            assert 'Emporio Music Store' in html
            assert response.headers['Content-Security-Policy']
        for asset in ('/app.js', '/style.css'):
            with urlopen(base + asset) as response:
                assert response.status == 200
        request = Request(base + '/api/chat', json.dumps({'message': 'teste'}).encode(), {'Content-Type': 'application/json'}, method='POST')
        with urlopen(request) as response:
            payload = json.load(response)
        assert payload['reply'] == '0: teste'
        request = Request(base + '/api/chat', json.dumps({'message': 'outro', 'session_id': payload['session_id']}).encode(), {'Content-Type': 'application/json'}, method='POST')
        with urlopen(request) as response:
            assert json.load(response)['reply'] == '2: outro'
        bad_origin = Request(base + '/api/chat', b'{}', {'Content-Type': 'application/json', 'Origin': 'https://evil.example'}, method='POST')
        with pytest.raises(HTTPError) as error:
            urlopen(bad_origin)
        assert error.value.code == 403
        huge = Request(base + '/api/chat', b'x' * 12001, {'Content-Type': 'application/json'}, method='POST')
        with pytest.raises(HTTPError) as error:
            urlopen(huge)
        assert error.value.code == 413
        with pytest.raises(HTTPError) as error:
            urlopen(base + '/../private')
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_frontend_renders_model_as_text():
    assert 'node.textContent = text' in (STATIC / 'app.js').read_text()
    assert 'innerHTML' not in (STATIC / 'app.js').read_text()
