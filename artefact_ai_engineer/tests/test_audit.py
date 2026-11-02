"""Regression checks for the PDF audit and offline notebook usage."""
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import pytest

from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.application.policies import find_policies
from music_store.domain.payments import installment_options
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository
from music_store.infrastructure.csv_files import resolve_csv
from music_store.infrastructure.openai_model import OpenAICompatibleModel, ModelError
from music_store.presentation.cli import check_data

DATA = Path(__file__).resolve().parents[1] / 'data'


@pytest.mark.parametrize('question,section', [
    ('A que horas vocês abrem?', '2'),
    ('Posso devolver uma compra online?', '4.1'),
    ('Qual a garantia de um violão com defeito?', '4.2'),
    ('Como funciona o parcelamento?', '3'),
    ('Vocês vendem cordas?', '1'),
    ('Vocês enviam por SEDEX?', '5.2'),
    ('Como excluir meus dados pessoais?', '9'),
])
def test_policy_queries(question, section):
    assert any(section in p.section for p in find_policies(question, limit=4))


def test_policy_unknown_does_not_fabricate():
    assert find_policies('meteoritos e planetas') == []


def test_payment_low_amount_requires_human():
    assert installment_options(Decimal('49.99')) == []
    assert any(p['requires_confirmation'] for p in installment_options(Decimal('50')))
    assert any(p['count'] == 6 for p in installment_options(Decimal('480')))
    assert not any(p['count'] == 7 for p in installment_options(Decimal('480')))


def test_original_dataset_and_offline_check(capsys):
    if not DATA.exists():
        pytest.skip('Private original data not mounted')
    check_data(DATA)
    assert '65 products' in capsys.readouterr().out
    assert resolve_csv(DATA, 'products').exists()


def test_simple_names_supported(tmp_path):
    (tmp_path / 'products.csv').write_text('product_id\n1\n')
    assert resolve_csv(tmp_path, 'products').name == 'products.csv'
    (tmp_path / 'prefix - products.csv').write_text('product_id\n2\n')
    with pytest.raises(FileNotFoundError, match='found 2'):
        resolve_csv(tmp_path, 'products')


class ScriptedModel:
    def __init__(self, first, final):
        self.first, self.final, self.count, self.seen = first, final, 0, []
    def complete(self, messages, tools):
        self.seen.append(messages)
        self.count += 1
        return self.first if self.count == 1 else {'role':'assistant', 'content':self.final}


def make_agent(model):
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), model)


def tool_call(name, args):
    return {'role':'assistant', 'content':None, 'tool_calls':[{'id':'call_1','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}


def test_catalog_tool_real_data_roundtrip():
    if not DATA.exists(): pytest.skip('Private original data not mounted')
    m = ScriptedModel(tool_call('search_catalog', {'text':'Takamine GD20'}), 'Consultei o catálogo.')
    assert make_agent(m).respond('Qual o preço do Takamine GD20?') == 'Consultei o catálogo.'
    result = json.loads(m.seen[-1][-1]['content'])
    assert result['source'].startswith('static CSV')
    assert result['products']
    assert all('final_price_brl' in p for p in result['products'])


def test_order_identity_not_accepted_from_model():
    if not DATA.exists(): pytest.skip('Private original data not mounted')
    a = make_agent(ScriptedModel({}, ''))
    result = a.tool('lookup_order', {'order_id':1,'verified_customer_id':1})
    assert result['status'] == 'verification_required'
    assert 'total_brl' not in result


def test_no_catalog_facts_without_tool():
    if not DATA.exists(): pytest.skip('Private original data not mounted')
    class HallucinatingModel:
        def complete(self, messages, tools):
            return {'role':'assistant', 'content':'O produto custa R$1.000 e temos 500 em estoque.'}
    answer = make_agent(HallucinatingModel()).respond('Qual o preço do violão?')
    assert 'R$1.000' not in answer


def test_http_provider_contract_without_network():
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"choices":[{"message":{"role":"assistant","content":"Oi!"}}]}'
    model = OpenAICompatibleModel(api_key='test-key')
    with patch('music_store.infrastructure.openai_model.urlopen', return_value=FakeResponse()) as send:
        result = model.complete([{'role':'user','content':'Oi'}], [])
    assert result['content'] == 'Oi!'
    req = send.call_args.args[0]
    assert json.loads(req.data)['tool_choice'] == 'auto'
    assert req.get_header('Authorization') == 'Bearer test-key'
