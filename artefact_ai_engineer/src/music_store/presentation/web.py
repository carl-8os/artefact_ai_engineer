"""Local-only HTTP chat interface. No third-party web framework required."""
from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository
from music_store.infrastructure.openai_model import ModelError
from music_store.infrastructure.model_factory import create_model

STATIC = Path(__file__).with_name('web_static')
MAX_BODY = 12_000
SESSION_TTL = 3600
MAX_SESSIONS = 200


class ChatSessions:
    """Thread-safe bounded session history; only stores public conversation turns."""

    def __init__(self, agent: MusicStoreAgent):
        self.agent = agent
        self._sessions: dict[str, tuple[float, list[dict]]] = {}
        self._lock = threading.RLock()

    def chat(self, session: str | None, message: str) -> tuple[str, str]:
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 4000:
            raise ValueError('Message must contain between 1 and 4000 characters.')
        with self._lock:
            now = time.monotonic()
            self._sessions = {k: v for k, v in self._sessions.items() if now - v[0] < SESSION_TTL}
            if not isinstance(session, str) or session not in self._sessions:
                session = secrets.token_urlsafe(32)
                if len(self._sessions) >= MAX_SESSIONS:
                    oldest = min(self._sessions, key=lambda key: self._sessions[key][0])
                    del self._sessions[oldest]
                self._sessions[session] = (now, [])
            _, history = self._sessions[session]
            # Serialize turns per process to avoid out-of-order conversation updates.
            reply = self.agent.respond(message, history=list(history))
            history.extend(({'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}))
            self._sessions[session] = (time.monotonic(), history[-16:])
            return session, reply


def make_handler(sessions: ChatSessions):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, code: int, data: dict):
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
            path = urlsplit(self.path).path
            if path not in files:
                return self._json(404, {'error': 'Not found'})
            filename, mime = files[path]
            content = (STATIC / filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self):
            if urlsplit(self.path).path != '/api/chat':
                return self._json(404, {'error': 'Not found'})
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            if origin not in (None, f'http://{host}'):
                return self._json(403, {'error': 'Origin not allowed'})
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                return self._json(415, {'error': 'Content-Type must be application/json'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                return self._json(400, {'error': 'Invalid request size'})
            if not 0 < size <= MAX_BODY:
                return self._json(413, {'error': 'Request too large or empty'})
            try:
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('JSON must be an object')
                session, reply = sessions.chat(data.get('session_id'), data.get('message'))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self._json(400, {'error': str(exc)})
            except ModelError as exc:
                return self._json(503, {'error': str(exc)})
            return self._json(200, {'session_id': session, 'reply': reply})

        def log_message(self, format, *args):
            # Avoid logging customer messages, request paths or session tokens.
            return

    return Handler


def serve(data: Path, host: str = '127.0.0.1', port: int = 8765):
    if host not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('The web interface must listen on localhost only.')
    agent = MusicStoreAgent(SearchCatalog(CsvCatalogRepository(data)), OrderLookup(CsvOrderRepository(data)), create_model(), policy_search=_policy_search())
    with ThreadingHTTPServer((host, port), make_handler(ChatSessions(agent))) as server:
        print(f'Emporio Music Store: http://127.0.0.1:{port} (Ctrl+C to stop)')
        server.serve_forever()


def _policy_search():
    import os
    if os.getenv('POLICY_RETRIEVAL', 'lexical').lower() == 'semantic':
        from music_store.infrastructure.semantic_policies import SemanticPolicySearch
        return SemanticPolicySearch().search
    from music_store.application.policies import find_policies
    return find_policies
