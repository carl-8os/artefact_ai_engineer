from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class Order:
    id: int
    customer_id: int
    status: str
    total: Decimal
    tracking_code: str | None
    estimated_delivery: str | None
    def __post_init__(self):
        if not self.total.is_finite() or self.total < 0 or self.status not in {"pending", "confirmed", "shipped", "delivered", "cancelled"}:
            raise ValueError("Invalid order")

@dataclass(frozen=True, slots=True)
class OrderItem:
    order_id: int
    product_id: int
    quantity: int
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Invalid quantity")
