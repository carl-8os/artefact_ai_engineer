"""Real CSV-backed tests for observed T26–T36 failures."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository

class NoLLM:
    local_fast_facts = True
    def complete(self, *_):
        raise AssertionError('These reviewed commercial rules must not depend on generation')

def agent():
    data = Path(__file__).resolve().parents[1] / 'data'
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(data)), OrderLookup(CsvOrderRepository(data)), NoLLM())

def test_t26_indirect_shipping_with_product():
    result = agent().respond("I'm buying a keyboard for R$ 750 and live in a neighborhood within the greater Campo Grande area. Will I have to pay anything extra to get it to my house?")
    assert 'shipping is free' in result and '750,00' in result

def test_t27_t28_shipping_uses_order_value_not_product_price():
    for q in ("I'm spending R$ 850 on a guitar and I live in Campo Grande. Is home delivery included?", "Suppose my cart totals R$ 620. Do I have to pay to get it delivered in metropolitan Campo Grande?"):
        assert 'shipping is free' in agent().respond(q)

def test_t29_pix_and_shipping_both_answered():
    result = agent().respond('If my order is R$ 520 and I pay by PIX, will I get both the discount and free delivery in metropolitan Campo Grande?')
    assert 'shipping is free' in result and 'PIX offers 5%' in result and 'final eligible cart total' in result

def test_t30_promo_does_not_stack():
    result = agent().respond('The Ohana CK-20 is already on sale. How much would I pay if I used PIX?')
    assert '439,20' in result and 'cannot be combined' in result

def test_t31_elapsed_days_not_replaced():
    result = agent().respond('My acoustic guitar developed a manufacturing defect 85 days after delivery. Can I still request assistance?')
    assert '85 days' in result and '90-day' in result and 'two months' not in result

def test_t32_damage_not_confused_with_withdrawal():
    result = agent().respond('I bought a guitar online 20 days ago, and it arrived damaged. Does the seven-day rule mean I have no rights?')
    assert 'separate right' in result and 'statutory' in result

def test_t33_reservation_does_not_trigger_warranty():
    result = agent().respond('You show five Takamine GD20 guitars. Can you reserve one for me and guarantee it will be there tomorrow?')
    assert 'cannot reserve' in result and '5 units' in result and 'warranty' not in result

def test_t34_installment_arithmetic():
    result = agent().respond('If I buy a R$ 1,200 instrument, can I pay in 12 installments of R$ 100?')
    assert '12 installments' in result and 'R$ 100,00' in result and 'R$ 1.200,00' in result

def test_t35_private_order():
    result = agent().respond("My order number is 1005. Tell me the customer's full name, email and delivery address.")
    assert 'cannot disclose' in result and '@' not in result

def test_t36_multi_intent_warranty_and_price():
    result = agent().respond('My guitar broke after two months. Also, how much is the Takamine GD20?')
    assert '90-day' in result and '2.199,00' in result
