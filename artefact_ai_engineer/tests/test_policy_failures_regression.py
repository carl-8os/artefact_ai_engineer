"""Regression tests for the real R03, R06 and R07 failures."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository
from music_store.application.policies import find_policies

DATA = Path(__file__).resolve().parents[1] / 'data'

class NoGeneration:
    def complete(self, *_):
        raise AssertionError('High-risk policy responses must not rely on ungrounded generation')


def agent(policy_search=find_policies):
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), NoGeneration(), policy_search=policy_search)


def test_warranty_two_months_no_invented_manufacturer_period():
    answer = agent().respond('My guitar stopped working after two months. Am I still protected?')
    assert '90-day' in answer and '30 days' in answer
    assert '12 to 24 months' not in answer
    assert 'may still be covered' in answer


def test_installments_not_confused_with_split_payment_methods():
    answer = agent().respond('Can I split my purchase into 12 credit card payments?')
    assert '12 installments' in answer and 'R$ 100' in answer
    assert 'R$ 2,000 threshold applies to combining different payment methods' in answer
    assert 'not to credit-card installments' in answer


def test_international_shipping_is_unknown_not_prohibited():
    answer = agent().respond('Does the store offer free international shipping?')
    assert 'do not specify' in answer
    assert 'confirm' in answer
    assert 'does not offer' not in answer


def test_matching_policy_required_for_warranty():
    answer = agent(lambda *_: []).respond('My guitar stopped working after two months. Am I still protected?')
    assert 'cannot verify' in answer


def test_matching_policy_required_for_installments():
    answer = agent(lambda *_: []).respond('Can I split my purchase into 12 credit card payments?')
    assert 'cannot verify' in answer


def test_semantic_search_hook_is_used():
    calls = []
    def search(question):
        calls.append(question)
        return find_policies(question)
    a = agent(search)
    a.respond('My guitar stopped working after two months. Am I still protected?')
    a.respond('Can I split my purchase into 12 credit card payments?')
    a.respond('Does the store offer free international shipping?')
    assert len(calls) == 3
