"""Regression coverage for the English submission build."""
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.application.policies import find_policies
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository

DATA = Path(__file__).resolve().parents[1] / "data"

class CaptureModel:
    def __init__(self):
        self.messages = None
    def complete(self, messages, tools):
        self.messages = messages
        return {"role": "assistant", "content": "Please contact the store for confirmation."}

def test_english_hours_retrieval():
    assert any("Saturday: 09:00" in p.text for p in find_policies("What are your Saturday opening hours?"))

def test_english_return_retrieval():
    assert any("7 calendar days" in p.text for p in find_policies("Can I return an online purchase?"))

def test_english_policy_prefetch():
    model = CaptureModel()
    agent = MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), model)
    agent.respond("What are your Saturday opening hours?")
    assert "Verified store policy excerpts" in model.messages[0]["content"]

def test_english_catalog_prefetch():
    model = CaptureModel()
    agent = MusicStoreAgent(SearchCatalog(CsvCatalogRepository(DATA)), OrderLookup(CsvOrderRepository(DATA)), model)
    agent.respond("What is the price of the Takamine GD20?")
    assert "Verified catalog snapshot" in model.messages[0]["content"]

def test_english_ui():
    html = (Path(__file__).resolve().parents[1] / "src/music_store/presentation/web_static/index.html").read_text()
    assert 'lang="en"' in html
    assert "New conversation" in html
