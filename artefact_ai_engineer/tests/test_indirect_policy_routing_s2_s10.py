"""Regression coverage for observed indirect policy questions and mixed intents."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository

class NoLLM:
    local_fast_facts = True
    def complete(self, *_):
        raise AssertionError('Verified policy questions should not require model speculation')

def agent():
    data = Path(__file__).resolve().parents[1] / 'data'
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(data)), OrderLookup(CsvOrderRepository(data)), NoLLM())

def test_s2_doorstep_without_amount_or_destination():
    result = agent().respond('Would bringing it to my doorstep add to the bill?')
    assert 'What is your delivery location and order total?' in result
    assert 'orders strictly above R$ 500' in result

def test_s3_installments_over_year():
    result = agent().respond('Can I spread the charge over a year?')
    assert '12 installments' in result and 'R$ 100' in result

def test_s4_keyboard_keys_no_sound():
    result = agent().respond('The keys quit making sound shortly after I got it.')
    assert '90-day statutory warranty' in result and 'Contact the store' in result

def test_s5_scan_code_for_pix():
    result = agent().respond('Can I pay by scanning a code and save money?')
    assert 'PIX offers 5%' in result and 'cannot be combined' in result

def test_s6_advertising_consent():
    result = agent().respond('Do you keep my details for advertisements?')
    assert 'Marketing messages require explicit consent' in result

def test_s10_pix_and_metro_shipping_both_answered():
    result = agent().respond('If I pay for a Takamine GD20 using PIX, what will it cost, and can you bring it to my home in metropolitan Campo Grande?')
    assert 'R$ 2.089,05' in result and 'shipping is free' in result

def test_unknown_shipping_total_not_assumed_from_context():
    result = agent().respond('Do you deliver to my home?')
    assert 'What is your delivery location and order total?' in result
