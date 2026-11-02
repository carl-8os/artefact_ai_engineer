from music_store.infrastructure.csv_files import resolve_csv
import csv
from decimal import Decimal
from pathlib import Path
from music_store.domain.models import Product, ProductStatus, Promotion
class CsvCatalogRepository:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
    def _rows(self, suffix):
        file = resolve_csv(self.directory, suffix)
        with file.open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))
    def list_products(self):
        return [Product(int(r['product_id']), int(r['category_id']), r['name'], Decimal(r['price_brl']), int(r['stock_quantity']), ProductStatus(r['status']), r['description']) for r in self._rows('products')]
    def list_promotions(self):
        return [Promotion(int(r['promotion_id']), int(r['product_id']), Decimal(r['discount_percent']), r['is_active'].strip().lower() in ('1', 'true')) for r in self._rows('promotions')]
