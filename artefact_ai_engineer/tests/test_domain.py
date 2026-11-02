from decimal import Decimal
import pytest
from music_store.domain.models import Product, ProductStatus, Promotion, quote_price, regional_shipping


def product(price="100.00", stock=1, status=ProductStatus.ACTIVE):
    return Product(1, 2, "Guitar", Decimal(price), stock, status)


def test_available_requires_active_and_stock():
    assert product().available
    assert not product(stock=0).available
    assert not product(status=ProductStatus.DISCONTINUED).available


def test_pix_discount():
    q = quote_price(product(), [], pix=True)
    assert (q.final_price, q.discount_source) == (Decimal("95.00"), "pix")


def test_promotion_does_not_stack_with_pix():
    q = quote_price(product(), [Promotion(1, 1, Decimal("10"), True)], pix=True)
    assert (q.final_price, q.discount_source) == (Decimal("90.00"), "promotion")


def test_round_half_up():
    assert quote_price(product("0.10"), [], pix=True).final_price == Decimal("0.10")


def test_multiple_active_promotions_fail_closed():
    with pytest.raises(ValueError, match="Multiple"):
        quote_price(product(), [Promotion(1, 1, Decimal("10"), True), Promotion(2, 1, Decimal("20"), True)])


def test_shipping_boundary():
    assert regional_shipping(Decimal("499.99")) == Decimal("35.00")
    assert regional_shipping(Decimal("500")) is None
    assert regional_shipping(Decimal("500.01")) == Decimal("0.00")


def test_invalid_values():
    with pytest.raises(ValueError):
        product(price="-1")
    with pytest.raises(ValueError):
        Promotion(1, 1, Decimal("101"), True)
