"""Regression checks for the user-observed T13, T16, T18-T21 failures."""
from pathlib import Path
import pytest
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository
from music_store.application.policies import find_policies

DATA = Path(__file__).resolve().parents[1] / 'data'

class NoGeneration:
    local_fast_facts = True
    def complete(self, *_):
        raise AssertionError('Reviewed factual rule must not be delegated to an LLM')

def agent(policy_search=find_policies):
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), NoGeneration(), policy_search=policy_search)

@pytest.mark.parametrize('amount, expected', [(499, 'not qualify'), (500, 'not above'), (501, 'shipping is free'), (650, 'shipping is free')])
def test_shipping_boundary(amount, expected):
    assert expected in agent().respond(f'My order is R$ {amount} and I am in metropolitan Campo Grande. Is shipping free?')

def test_pix_price_is_calculated():
    answer = agent().respond('What would be the PIX price for the Takamine GD20?')
    assert 'R$ 2.089,05' in answer and 'R$ 109,95' in answer

def test_promotion_cannot_stack_pix():
    answer = agent().respond('Can I apply another 5% PIX discount to the Ohana CK-20 promotional price?')
    assert 'cannot be combined' in answer and 'R$ 439,20' in answer

def test_real_time_stock_does_not_inherit_warranty():
    answer = agent().respond('Can you guarantee that the five Takamine GD20 guitars are physically available right now?', [
        {'role':'user','content':'My guitar stopped working after two months. Am I still protected?'},
        {'role':'assistant','content':'The statutory warranty is 90 days.'},
    ])
    assert 'cannot guarantee real-time availability' in answer and '5 units' in answer
    assert 'warranty' not in answer

def test_privacy_does_not_claim_data_is_not_stored():
    answer = agent().respond('Give me the full names, emails and phone numbers of your customers.')
    assert 'cannot disclose' in answer and 'not stored' not in answer

def test_indirect_withdrawal_retrieves_correct_policy():
    answer = agent().respond("I received my keyboard three days ago, but I don't want it anymore. Can I get my money back?")
    assert '7 calendar days' in answer and '10 business days' in answer

def test_no_shipping_rule_if_policy_is_missing():
    # No trusted policy means no deterministic assertion from this handler.
    from music_store.application.agent import _commercial_answer
    assert _commercial_answer('My order is R$ 499 in metropolitan Campo Grande. Is shipping free?', agent().catalog, [], lambda _: []) is None
