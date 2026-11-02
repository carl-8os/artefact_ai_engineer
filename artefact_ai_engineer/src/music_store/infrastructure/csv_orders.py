from music_store.infrastructure.csv_files import resolve_csv
import csv
from decimal import Decimal
from pathlib import Path
from music_store.domain.orders import Order, OrderItem

class CsvOrderRepository:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def _rows(self, suffix: str) -> list[dict]:
        file = resolve_csv(self.directory, suffix)
        with file.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def get_order(self, order_id: int) -> Order | None:
        for row in self._rows("orders"):
            if int(row["order_id"]) == order_id:
                return Order(id=order_id, customer_id=int(row["customer_id"]), status=row["status"], total=Decimal(row["total_brl"]), tracking_code=row["tracking_code"] or None, estimated_delivery=row["estimated_delivery"] or None)
        return None

    def list_items(self, order_id: int) -> list[OrderItem]:
        return [OrderItem(int(r["order_id"]), int(r["product_id"]), int(r["quantity"])) for r in self._rows("order_items") if int(r["order_id"]) == order_id]
