from dataclasses import dataclass
import re
import unicodedata
from decimal import Decimal
from music_store.application.ports import CatalogRepository
from music_store.domain.models import Product, PriceQuote, quote_price
@dataclass(frozen=True)
class ProductResult:
    product: Product
    quote: PriceQuote
def _normalize(value: str) -> str:
    return ''.join(char for char in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(char))


def _terms(value: str) -> set[str]:
    return set(re.findall(r'[a-z0-9]+', _normalize(value)))


class SearchCatalog:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository
    def execute(self, *, text='', max_price: Decimal | None = None, available_only=True, pix=False) -> list[ProductResult]:
        if max_price is not None and max_price < 0:
            raise ValueError('Negative maximum price')
        promotions = self.repository.list_promotions()
        results = []
        for p in self.repository.list_products():
            if available_only and not p.available: continue
            if text and not (_terms(text) <= _terms(p.name + ' ' + p.description) or _normalize(text) in _normalize(p.name + ' ' + p.description)): continue
            quote = quote_price(p, promotions, pix=pix)
            if max_price is not None and quote.final_price > max_price: continue
            results.append(ProductResult(p, quote))
        return sorted(results, key=lambda r: (r.quote.final_price, r.product.id))
