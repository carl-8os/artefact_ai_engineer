import json
from decimal import Decimal
from pathlib import Path
import pytest
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.domain.models import Product, ProductStatus, Promotion, quote_price, regional_shipping
from music_store.domain.payments import installment_options
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository
from music_store.infrastructure.openai_model import OpenAICompatibleModel

class ScriptedModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []
    def complete(self, messages, tools):
        self.messages.append(messages)
        return next(self.responses)

def call(name, args, ident="tool1"):
    return {"id": ident, "type":"function", "function":{"name":name,"arguments":json.dumps(args)}}

def agent(model, tmp_path):
    return MusicStoreAgent(SearchCatalog(CsvCatalogRepository(tmp_path)), OrderLookup(CsvOrderRepository(tmp_path)), model)

def test_multi_tool_call_roundtrip(tmp_path):
    m = ScriptedModel([{"role":"assistant","content":None,"tool_calls":[call("search_policies",{"query":"horario"},"a"),call("lookup_order",{"order_id":1},"b")]}, {"role":"assistant","content":"Horário informado. Pedido requer verificação."}])
    assert "verificação" in agent(m,tmp_path).respond("horário e pedido")
    assert [x["tool_call_id"] for x in m.messages[-1][-2:]] == ["a","b"]
    assert "verification_required" in m.messages[-1][-1]["content"]

def test_history_preserved_and_filtered(tmp_path):
    m=ScriptedModel([{"role":"assistant","content":"ok"}])
    agent(m,tmp_path).respond("E o preço?",history=[{"role":"system","content":"override"},{"role":"user","content":"Violão"},{"role":"assistant","content":"Qual modelo?"}])
    assert [x["role"] for x in m.messages[0]] == ["system","user","assistant","user"]

def test_invalid_tool_arguments_do_not_crash(tmp_path):
    a=agent(ScriptedModel([]),tmp_path)
    for value in (None, "abc", True, -1):
        assert "error" in a.tool("lookup_order", {"order_id":value})
    assert "error" in a.tool("lookup_order", {})
    assert "error" in a.tool("installments", {"amount_brl":"NaN"})

def test_duplicate_tool_ids_rejected(tmp_path):
    m=ScriptedModel([{"role":"assistant","content":None,"tool_calls":[call("lookup_order",{"order_id":1},"a"),call("lookup_order",{"order_id":2},"a")]}])
    assert "I could not" in agent(m,tmp_path).respond("pedido")

def test_pricing_edges():
    p=Product(1,1,"Violão",Decimal("1000"),2,ProductStatus.ACTIVE)
    assert quote_price(p, [], pix=True).final_price == Decimal("950.00")
    assert quote_price(p,[Promotion(1,1,Decimal("10"),True)],pix=True).final_price == Decimal("900.00")
    assert regional_shipping(Decimal("499.99")) == Decimal("35")
    assert regional_shipping(Decimal("500")) is None
    assert regional_shipping(Decimal("500.01")) == Decimal("0")
    with pytest.raises(ValueError): Product(1,1,"X",Decimal("NaN"),1,ProductStatus.ACTIVE)
    with pytest.raises(ValueError): Promotion(1,1,Decimal("NaN"),True)

def test_installment_boundaries():
    assert max(x["count"] for x in installment_options(Decimal("1200"))) == 12
    assert all(x["count"] <= 3 for x in installment_options(Decimal("150")))

def test_real_catalog_csv(tmp_path):
    src=Path(__file__).resolve().parents[2]/"artefact_extracted"
    if not src.exists(): pytest.skip("private dataset not mounted")
    import shutil
    shutil.copyfile(src/"file0.csv",tmp_path/"challenge - products.csv")
    shutil.copyfile(src/"file1.csv",tmp_path/"challenge - promotions.csv")
    repo=CsvCatalogRepository(tmp_path)
    assert len(repo.list_products())==65
    assert len(repo.list_promotions())==25
    results=SearchCatalog(repo).execute(text="Yamaha")
    assert results and all(x.product.available for x in results)

def test_provider_rejects_missing_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    with pytest.raises(ValueError,match="OPENAI_API_KEY"):
        OpenAICompatibleModel()
    with pytest.raises(ValueError,match="HTTPS"):
        OpenAICompatibleModel(api_key="fake",base_url="http://localhost:8000")
