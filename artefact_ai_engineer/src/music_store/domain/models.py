from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

class ProductStatus(str, Enum):
    ACTIVE = 'active'
    DISCONTINUED = 'discontinued'
    COMING_SOON = 'coming_soon'

@dataclass(frozen=True, slots=True)
class Product:
    id: int
    category_id: int
    name: str
    price: Decimal
    stock_quantity: int
    status: ProductStatus
    description: str = ''
    def __post_init__(self):
        if not self.price.is_finite() or self.price < 0 or self.stock_quantity < 0 or not self.name.strip():
            raise ValueError('Invalid product values')
    @property
    def available(self):
        return self.status == ProductStatus.ACTIVE and self.stock_quantity > 0

@dataclass(frozen=True, slots=True)
class Promotion:
    id: int
    product_id: int
    discount_percent: Decimal
    active: bool
    def __post_init__(self):
        if not self.discount_percent.is_finite() or not 0 <= self.discount_percent <= 100:
            raise ValueError('Invalid promotion discount')

@dataclass(frozen=True, slots=True)
class PriceQuote:
    list_price: Decimal
    final_price: Decimal
    discount_percent: Decimal
    discount_source: str

def quote_price(product: Product, promotions: list[Promotion], *, pix=False) -> PriceQuote:
    active = [p for p in promotions if p.product_id == product.id and p.active]
    if len(active) > 1:
        raise ValueError('Multiple active promotions require review')
    discount, source = (active[0].discount_percent, 'promotion') if active else ((Decimal('5'), 'pix') if pix else (Decimal('0'), 'none'))
    total = (product.price * (1 - discount / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return PriceQuote(product.price, total, discount, source)

def regional_shipping(total: Decimal) -> Decimal | None:
    if total < 0:
        raise ValueError('Negative total')
    if total == 500:
        return None
    return Decimal('0.00') if total > 500 else Decimal('35.00')
