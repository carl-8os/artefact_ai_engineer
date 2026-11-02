"""Real-user regression cases: installment amount, store scope, mixed catalog/policy."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository


class ModelMustNotAnswer:
    local_fast_facts = True

    def complete(self, *_):
        raise AssertionError('Verified business flows must not fall through to the LLM')


def make_agent():
    data = Path(__file__).resolve().parents[1] / 'data'
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(data)),
                           OrderLookup(CsvOrderRepository(data)), ModelMustNotAnswer())


def test_t4_amount_and_year_are_used_without_asking_again():
    answer = make_agent().respond('I want to buy a guitar for R$ 1,800. Can I spread the payment over a whole year without interest?')
    assert '12 installments' in answer
    assert 'R$ 1.800,00' in answer
    assert 'R$ 150,00' in answer
    assert 'What is the purchase total?' not in answer


def test_t4_below_minimum_is_not_offered_as_eligible():
    answer = make_agent().respond('Can I pay R$ 600 over a whole year?')
    assert 'below' in answer and 'R$ 100,00' in answer


def test_t7_python_automation_is_out_of_store_scope():
    answer = make_agent().respond('Can you help me write a Python script to automate my computer?')
    assert 'outside' in answer and 'Emporio Music Store' in answer
    assert 'sample script' not in answer


def test_t8_catalog_price_and_online_return_are_both_present():
    answer = make_agent().respond('How much does the Yamaha FG800 cost, and if I buy it online, can I return it if I change my mind?')
    assert 'Yamaha FG800' in answer and 'R$ 1.299,00' in answer
    assert '7 calendar days' in answer and 'return shipping' in answer
    assert '10 business days' in answer


def test_t8_return_only_keeps_policy_answer():
    answer = make_agent().respond('I bought a guitar online. Can I return it if I change my mind?')
    assert '7 calendar days' in answer


def test_out_of_scope_does_not_block_store_technical_questions():
    answer = make_agent().respond('How much does the Yamaha FG800 cost?')
    assert 'R$ 1.299,00' in answer
