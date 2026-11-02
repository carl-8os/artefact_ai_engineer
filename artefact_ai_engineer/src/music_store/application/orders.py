from typing import Protocol
from music_store.domain.orders import Order, OrderItem

class OrderRepository(Protocol):
    def get_order(self, order_id: int) -> Order | None: ...
    def list_items(self, order_id: int) -> list[OrderItem]: ...

class OrderLookup:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: int, *, verified_customer_id: int | None = None) -> dict:
        if verified_customer_id is None:
            return {"status": "verification_required", "message": "Order details require verified customer identity. This demo has no identity verification flow."}
        order = self.repository.get_order(order_id)
        if order is None or order.customer_id != verified_customer_id:
            return {"status": "not_found", "message": "No accessible order found."}
        return {"status": order.status, "order_id": order.id, "total_brl": str(order.total), "tracking_code": order.tracking_code, "estimated_delivery": order.estimated_delivery, "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in self.repository.list_items(order_id)]}
