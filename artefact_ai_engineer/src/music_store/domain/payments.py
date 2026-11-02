"""Credit-card quotes: never assert eligibility where manual sections conflict."""
from decimal import Decimal, ROUND_HALF_UP


def installment_options(amount: Decimal) -> list[dict]:
    if not amount.is_finite() or amount <= 0:
        raise ValueError('Invalid purchase amount')
    options = []
    for count in range(1, 13):
        installment = (amount / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if count <= 3:
            # Policy §3 conflicts with §3.1; amounts under BRL 50 require human review.
            if amount < Decimal('50'):
                continue
            minimum = None
        elif count <= 6:
            minimum = Decimal('80')
        else:
            minimum = Decimal('100')
        if minimum is None or installment >= minimum:
            options.append({'count': count, 'approx_installment_brl': str(installment),
                            'minimum_brl': str(minimum) if minimum is not None else None,
                            'requires_confirmation': count <= 3})
    return options
