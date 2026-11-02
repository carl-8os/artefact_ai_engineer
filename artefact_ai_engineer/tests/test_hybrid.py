"""End-to-end application-level tests with the original catalog and scripted LLM."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository

DATA = Path(__file__).resolve().parents[1] / 'data'


class CaptureModel:
    def __init__(self, reply):
        self.reply = reply
        self.messages = []
    def complete(self, messages, tools):
        self.messages.append(messages)
        return {'role': 'assistant', 'content': self.reply}


def agent(model):
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), model)


def test_specific_product_prefetch():
    model = CaptureModel('Consultei o catálogo.')
    agent(model).respond('Qual o preço do Takamine GD20?')
    assert 'Verified catalog snapshot' in model.messages[0][0]['content']
    assert 'Takamine GD20' in model.messages[0][0]['content']


def test_followup_resolves_previous_product():
    model = CaptureModel('Vou verificar.')
    agent(model).respond('E o preço dele?', history=[{'role':'user','content':'Quero o Takamine GD20'}, {'role':'assistant','content':'Claro.'}])
    assert 'Takamine GD20' in model.messages[0][0]['content']


def test_policy_prefetch_and_scope():
    model = CaptureModel('A loja fecha aos domingos.')
    agent(model).respond('Qual o horário de sábado?')
    assert 'Verified store policy excerpts' in model.messages[0][0]['content']
    assert '09:00' in model.messages[0][0]['content']


def test_hallucinated_price_is_rejected():
    model = CaptureModel('O Takamine GD20 custa R$ 999999,00.')
    result = agent(model).respond('Qual o preço do Takamine GD20?')
    assert '999999' not in result
    assert 'verify' in result


def test_no_private_data_in_prefetch():
    model = CaptureModel('É necessária verificação de identidade.')
    agent(model).respond('Quero consultar meu pedido 10')
    assert 'customer_id' not in model.messages[0][0]['content']


def test_catalog_accent_insensitive():
    results = agent(CaptureModel('ok')).catalog.execute(text='takamine gd20')
    assert results
