import json
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.application.policies import find_policies
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository

class FakeModel:
    def __init__(self): self.calls = 0
    def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return {"role":"assistant", "content":None,"tool_calls":[{"id":"call_1","type":"function","function":{"name":"search_policies","arguments":json.dumps({"query":"horário"})}}]}
        assert messages[-1]["role"] == "tool"
        assert "09:00" in messages[-1]["content"]
        return {"role":"assistant","content":"Atendemos de segunda a sexta, das 9h às 18h."}

def test_policies():
    assert "09:00" in find_policies("Qual é o horário?")[0].text
    assert "7 calendar" in find_policies("Quero devolução")[0].text

def test_agent_fake_llm(tmp_path):
    agent = MusicStoreAgent(SearchCatalog(CsvCatalogRepository(tmp_path)), OrderLookup(CsvOrderRepository(tmp_path)), FakeModel())
    assert "segunda" in agent.respond("Qual o horário?")
    assert agent.tool("lookup_order", {"order_id":1})["status"] == "verification_required"
    assert agent.tool("search_policies", {"query":"frete"})["policies"]

def test_invalid_input(tmp_path):
    import pytest
    agent = MusicStoreAgent(SearchCatalog(CsvCatalogRepository(tmp_path)), OrderLookup(CsvOrderRepository(tmp_path)), FakeModel())
    with pytest.raises(ValueError): agent.respond(" ")

def test_real_csv_orders(tmp_path):
    directory = Path(__file__).resolve().parents[2] / "artefact_extracted"
    if not directory.exists():
        import pytest; pytest.skip("Private CSV fixtures not available")
    import shutil
    shutil.copyfile(directory / "file5.csv", tmp_path / "challenge - orders.csv")
    shutil.copyfile(directory / "file4.csv", tmp_path / "challenge - order_items.csv")
    repo = CsvOrderRepository(tmp_path)
    assert repo.get_order(1).status == "delivered"
    assert len(repo.list_items(15)) == 2
