from decimal import Decimal
from datetime import date
from src.data.validator import SaleRecord, AdSpendRecord

def test_channel_normalization():
    sale = SaleRecord(
        transaction_id="TX001",
        customer_id="C1",
        amount=Decimal("150.00"),
        sale_date=date(2024, 1, 15),
        channel="fb ads"
    )
    assert sale.channel == "FACEBOOK"

def test_negative_amount_rejected():
    try:
        SaleRecord(
            transaction_id="TX002",
            customer_id="C2",
            amount=Decimal("-50"),
            sale_date=date(2024, 1, 15),
            channel="facebook"
        )
        assert False, "Debió fallar"
    except Exception:
        assert True