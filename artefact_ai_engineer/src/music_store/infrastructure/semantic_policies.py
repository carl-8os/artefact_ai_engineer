"""Optional local policy embeddings. Never embeds customer or order records."""
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from music_store.application.policies import POLICIES, Policy, find_policies


class EmbeddingUnavailable(RuntimeError):
    """Ollama embeddings cannot be used at this time."""


class OllamaEmbeddings:
    def __init__(self, url: str = 'http://127.0.0.1:11434', model: str = 'nomic-embed-text:latest'):
        self.url = url.rstrip('/')
        self.model = model

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({'model': self.model, 'input': text}).encode('utf-8')
        req = Request(self.url + '/api/embed', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(req, timeout=15) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise EmbeddingUnavailable('Local Ollama embedding endpoint unavailable') from exc
        embeddings = data.get('embeddings') if isinstance(data, dict) else None
        if not isinstance(embeddings, list) or len(embeddings) != 1:
            raise EmbeddingUnavailable('Invalid Ollama embedding response')
        values = embeddings[0]
        if not isinstance(values, list) or not values or not all(isinstance(x, (float, int)) and math.isfinite(x) for x in values):
            raise EmbeddingUnavailable('Invalid embedding vector')
        return [float(x) for x in values]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    denominator = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / denominator if denominator else 0.0


class SemanticPolicySearch:
    """Lazy, cached policy index. Lexical results take precedence for exact matches."""
    def __init__(self, embedder=None, cache_path: Path | None = None, threshold: float = 0.43):
        self.embedder = embedder or OllamaEmbeddings(
            os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'),
            os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text:latest'))
        self.cache_path = cache_path or Path('.cache/policy_embeddings.json')
        self.threshold = threshold
        self._vectors = None
        self._disabled = False

    def _fingerprint(self) -> str:
        content = json.dumps([(p.topic, p.text, p.section) for p in POLICIES], ensure_ascii=False)
        return hashlib.sha256((self.embedder.model + '\n' + content).encode('utf-8')).hexdigest()

    def _index(self):
        if self._vectors is not None:
            return self._vectors
        fingerprint = self._fingerprint()
        try:
            cached = json.loads(self.cache_path.read_text(encoding='utf-8'))
            vectors = cached.get('vectors')
            if cached.get('fingerprint') == fingerprint and isinstance(vectors, list) and len(vectors) == len(POLICIES) and all(isinstance(v, list) and v for v in vectors):
                self._vectors = vectors
                return vectors
        except (OSError, ValueError, AttributeError):
            pass
        vectors = [self.embedder.embed(p.topic + '\n' + p.text) for p in POLICIES]
        self._vectors = vectors
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.cache_path.with_suffix('.tmp')
            temp.write_text(json.dumps({'fingerprint': fingerprint, 'vectors': vectors}), encoding='utf-8')
            temp.replace(self.cache_path)
        except OSError:
            pass  # Cache is an optimization; retrieval still works in memory.
        return vectors

    def search(self, question: str, limit: int = 3) -> list[Policy]:
        if limit < 1:
            return []
        lexical = find_policies(question, limit)
        if self._disabled:
            return lexical
        try:
            query = self.embedder.embed(question)
            scores = [(cosine(query, v), i) for i, v in enumerate(self._index())]
        except EmbeddingUnavailable:
            self._disabled = True
            return lexical
        # Keep exact lexical matches first; semantic results fill the remaining slots.
        # Reserve room for semantic neighbors: lexical top-3 previously filled
        # every slot and silently prevented embeddings from affecting retrieval.
        result = lexical[:1]
        for score, index in sorted(scores, key=lambda row: (-row[0], row[1])):
            policy = POLICIES[index]
            if score < self.threshold or len(result) >= limit:
                break
            if policy not in result:
                result.append(policy)
        return result
