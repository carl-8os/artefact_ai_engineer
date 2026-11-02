"""Regression tests for observed local-model factual failures."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository

DATA = Path(__file__).resolve().parents[1] / 'data'

class NoCallModel:
    local_fast_facts = True
    def complete(self, messages, tools):
        raise AssertionError('Deterministic factual question must not call the model')

def agent():
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), NoCallModel())

def test_saturday_no_noon():
    answer = agent().respond('What time do you close on Saturday?')
    assert '1:00 PM' in answer and 'noon' not in answer

def test_exact_price_and_stock():
    answer = agent().respond('How much does the Takamine GD20 cost?')
    assert 'R$ 2.199,00' in answer and '5 units' in answer

def test_guitars_not_ukuleles():
    answer = agent().respond('Show me acoustic guitars under R$ 1,000.')
    assert 'Tagima Memphis AC-39' in answer
    assert 'Kala KA-15S' not in answer and 'Kalani KAL-700T' not in answer
    assert 'R$ 429,90' in answer

def test_budget_no_matches():
    answer = agent().respond('Show me acoustic guitars under R$ 1.')
    assert 'No available acoustic guitars' in answer

def test_promotion_price_consistent():
    answer = agent().respond('How much does the Takamine GD20 cost?')
    assert 'no active product promotion' in answer


def test_active_promotions_are_grounded_and_do_not_call_llm():
    from decimal import Decimal
    from music_store.domain.models import quote_price
    instance = agent()
    response = instance.respond('Which musical instruments are currently on sale?')
    active = [p for p in instance.catalog.repository.list_promotions() if p.active]
    products = {p.id: p for p in instance.catalog.repository.list_products()}
    eligible = [p for p in active if products[p.product_id].available]
    assert eligible
    assert response.startswith('Active instrument promotions')
    for promotion in eligible:
        product = products[promotion.product_id]
        quote = quote_price(product, active)
        assert product.name in response
        assert _format_brl(quote.final_price) in response
        assert _format_brl(quote.list_price) in response
    assert 'PIX discount cannot be combined' in response


def _format_brl(value):
    formatted = f'{value:,.2f}'
    return 'R$ ' + formatted.replace(',', '_').replace('.', ',').replace('_', '.')


def test_inactive_promotions_not_presented_as_active():
    instance = agent()
    response = instance.respond('Which musical instruments are currently on sale?')
    active = {p.product_id for p in instance.catalog.repository.list_promotions() if p.active}
    for product in instance.catalog.repository.list_products():
        if product.id not in active:
            assert f'{product.name} —' not in response


def test_promotion_queries_in_portuguese():
    assert agent().respond('Quais instrumentos estão em promoção?').startswith('Active instrument promotions')
