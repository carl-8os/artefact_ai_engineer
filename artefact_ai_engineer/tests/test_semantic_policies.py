import json
from music_store.application.policies import POLICIES
from music_store.infrastructure.semantic_policies import SemanticPolicySearch, EmbeddingUnavailable, cosine


class FakeEmbeddings:
    model = 'fake-test'
    def __init__(self):
        self.calls = 0
    def embed(self, text):
        self.calls += 1
        if text == 'What happens if my purchase is faulty?':
            return [0.0, 1.0]
        if 'defect faulty warranty' in text:
            return [0.0, 1.0]
        return [1.0, 0.0]


def test_cosine_handles_zero_and_dimensions():
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0
    assert cosine([0, 0], [1, 0]) == 0
    assert cosine([1], [1, 2]) == 0


def test_semantic_retrieves_policy_and_caches(tmp_path):
    fake = FakeEmbeddings()
    path = tmp_path / 'index.json'
    engine = SemanticPolicySearch(fake, path)
    result = engine.search('What happens if my purchase is faulty?')
    assert any('90-day' in p.text for p in result)
    assert path.exists()
    calls = fake.calls
    engine.search('What happens if my purchase is faulty?')
    assert fake.calls == calls + 1
    second = FakeEmbeddings()
    SemanticPolicySearch(second, path).search('What happens if my purchase is faulty?')
    assert second.calls == 1  # index read from disk


def test_cache_invalidation(tmp_path):
    path = tmp_path / 'index.json'
    path.write_text(json.dumps({'fingerprint': 'old', 'vectors': [[1,0]]*len(POLICIES)}))
    fake = FakeEmbeddings()
    SemanticPolicySearch(fake, path).search('What happens if my purchase is faulty?')
    assert fake.calls == len(POLICIES) + 1


def test_lexical_fallback(tmp_path):
    class Offline:
        model = 'offline'
        def embed(self, text):
            raise EmbeddingUnavailable('offline')
    engine = SemanticPolicySearch(Offline(), tmp_path / 'index.json')
    assert any('09:00' in p.text for p in engine.search('Saturday hours'))
    assert engine.search('Saturday hours')


def test_no_customer_data_in_index(tmp_path):
    path = tmp_path / 'index.json'
    SemanticPolicySearch(FakeEmbeddings(), path).search('Saturday hours')
    content = path.read_text()
    assert 'customer_id' not in content
    assert 'email' not in content
