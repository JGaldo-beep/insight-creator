import os
import random
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from pydantic import ValidationError

from src.data.models import FactSales, FactAdSpend, FactCampaignPerformance
from src.data.validator import SaleRecord, AdSpendRecord, ValidationResult

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://insight_user:insight_pass@localhost:5432/insight_db"
)

engine = create_engine(DATABASE_URL)


# --------------------------------
# Generadores de datos simulados
# --------------------------------


def generate_sales_data(days: int = 30) -> list[dict]:
    """Simula la Fuente A — datos crudos de ventas con ruido intencional."""
    channels_raw = [
        "facebook",
        "fb ads",
        "FB Ads",
        "Facebook",  # todos son FACEBOOK
        "google",
        "Google Ads",
        "google_ads",  # todos son GOOGLE_ADS
        "instagram",
        "IG",
        "ig ads",  # todos son INSTAGRAM
    ]
    records = []
    today = datetime.now(timezone.utc).date()

    for i in range(days * 3):
        sale_date = today - timedelta(days=random.randint(0, days))
        records.append(
            {
                "transaction_id": f"TX-{i:05d}",
                "customer_id": f"C-{random.randint(1, 50):03d}",
                "amount": str(round(random.uniform(10, 500), 2)),
                "sale_date": sale_date.isoformat(),
                "channel": random.choice(channels_raw),
            }
        )

    # Inyectamos datos sucios a propósito para probar el validator
    records.append(
        {
            "transaction_id": "TX-BAD-01",
            "customer_id": "C-999",
            "amount": "-100",
            "sale_date": date.today().isoformat(),
            "channel": "facebook",
        }
    )
    records.append(
        {
            "transaction_id": "TX-BAD-02",
            "customer_id": "C-999",
            "amount": "200",
            "sale_date": "2099-01-01",
            "channel": "facebook",
        }
    )
    records.append(
        {
            "transaction_id": "TX-BAD-03",
            "customer_id": "C-999",
            "amount": "200",
            "sale_date": date.today().isoformat(),
            "channel": "tiktok_ads",
        }
    )

    return records


def generate_ad_spend_data(days: int = 30) -> list[dict]:
    """Simula la Fuente B — JSON de inversión publicitaria."""
    channels = ["FACEBOOK", "GOOGLE_ADS", "INSTAGRAM"]
    records = []
    today = datetime.now(timezone.utc).date()

    for day_offset in range(days):
        spend_date = today - timedelta(days=day_offset)
        for channel in channels:
            impressions = random.randint(1000, 50000)
            clicks = random.randint(50, min(impressions, 2000))
            records.append(
                {
                    "spend_date": spend_date.isoformat(),
                    "channel": channel,
                    "cost": str(round(random.uniform(50, 1000), 2)),
                    "impressions": impressions,
                    "clicks": clicks,
                }
            )

    return records


# --------------------------------
# Capa de validación
# --------------------------------


def validate_sales(raw_records: list[dict]) -> ValidationResult:
    result = ValidationResult()
    for raw in raw_records:
        try:
            record = SaleRecord(
                transaction_id=raw["transaction_id"],
                customer_id=raw["customer_id"],
                amount=Decimal(str(raw["amount"])),
                sale_date=date.fromisoformat(str(raw["sale_date"])),
                channel=raw["channel"],
            )
            result.add_valid(record)
        except (ValidationError, ValueError) as e:
            result.add_rejected(raw, str(e))
    return result


def validate_ad_spend(raw_records: list[dict]) -> ValidationResult:
    result = ValidationResult()
    for raw in raw_records:
        try:
            record = AdSpendRecord(
                spend_date=date.fromisoformat(str(raw["spend_date"])),
                channel=raw["channel"],
                cost=Decimal(str(raw["cost"])),
                impressions=int(raw["impressions"]),
                clicks=int(raw["clicks"]),
            )
            result.add_valid(record)
        except (ValidationError, ValueError) as e:
            result.add_rejected(raw, str(e))
    return result


# --------------------------------
# Persistencia en PostgreSQL
# --------------------------------


def persist_sales(session: Session, result: ValidationResult) -> int:
    """Inserta ventas válidas evitando duplicados."""
    inserted = 0
    for record in result.valid:
        if not isinstance(record, SaleRecord):
            continue

        # Deduplicación: si ya existe el transaction_id, se omite
        exists = session.scalar(
            select(func.count()).where(
                FactSales.transaction_id == record.transaction_id
            )
        )
        if exists:
            continue

        session.add(
            FactSales(
                transaction_id=record.transaction_id,
                customer_id=record.customer_id,
                amount=record.amount,
                sale_date=record.sale_date,
                channel_key=record.channel,
            )
        )
        inserted += 1

    session.commit()
    return inserted


def persist_ad_spend(session: Session, result: ValidationResult) -> int:
    """Inserta inversión publicitaria evitando duplicados por (fecha, canal)."""
    inserted = 0
    for record in result.valid:
        if not isinstance(record, AdSpendRecord):
            continue

        exists = session.scalar(
            select(func.count()).where(
                FactAdSpend.spend_date == record.spend_date,
                FactAdSpend.channel_key == record.channel,
            )
        )
        if exists:
            continue

        session.add(
            FactAdSpend(
                spend_date=record.spend_date,
                channel_key=record.channel,
                cost=record.cost,
                impressions=record.impressions,
                clicks=record.clicks,
            )
        )
        inserted += 1

    session.commit()
    return inserted


def refresh_campaign_performance(session: Session) -> None:
    """
    Recalcula fact_campaign_performance unificando
    ventas + inversión por día y canal.
    """
    # Ventas agregadas por día y canal
    sales_agg = session.execute(
        select(
            FactSales.sale_date,
            FactSales.channel_key,
            func.sum(FactSales.amount).label("total_revenue"),
            func.count(FactSales.id).label("total_transactions"),
            func.count(func.distinct(FactSales.customer_id)).label("unique_customers"),
        ).group_by(FactSales.sale_date, FactSales.channel_key)
    ).all()

    for row in sales_agg:
        # Busca la inversión correspondiente
        spend = session.scalar(
            select(FactAdSpend).where(
                FactAdSpend.spend_date == row.sale_date,
                FactAdSpend.channel_key == row.channel_key,
            )
        )

        # Upsert en fact_campaign_performance
        existing = session.scalar(
            select(FactCampaignPerformance).where(
                FactCampaignPerformance.perf_date == row.sale_date,
                FactCampaignPerformance.channel_key == row.channel_key,
            )
        )

        if existing:
            existing.total_revenue = row.total_revenue
            existing.total_transactions = row.total_transactions
            existing.unique_customers = row.unique_customers
            existing.total_ad_spend = spend.cost if spend else Decimal("0")
            existing.total_impressions = spend.impressions if spend else 0
            existing.total_clicks = spend.clicks if spend else 0
        else:
            session.add(
                FactCampaignPerformance(
                    perf_date=row.sale_date,
                    channel_key=row.channel_key,
                    total_revenue=row.total_revenue,
                    total_transactions=row.total_transactions,
                    unique_customers=row.unique_customers,
                    total_ad_spend=spend.cost if spend else Decimal("0"),
                    total_impressions=spend.impressions if spend else 0,
                    total_clicks=spend.clicks if spend else 0,
                )
            )

    session.commit()


# ---------------------------------------------
# Punto de entrada principal
# ---------------------------------------------


def run_pipeline() -> dict:
    """Ejecuta el pipeline completo de ingesta."""
    print("Iniciando pipeline de ingesta...")

    # 1. Generar datos simulados
    raw_sales = generate_sales_data(days=30)
    raw_spend = generate_ad_spend_data(days=30)
    print(f"Datos generados - Ventas: {len(raw_sales)} | Inversión: {len(raw_spend)}")

    # 2. Validar
    sales_result = validate_sales(raw_sales)
    spend_result = validate_ad_spend(raw_spend)
    print(f"Ventas     - {sales_result.summary}")
    print(f"Inversión  - {spend_result.summary}")

    if sales_result.rejected:
        print("Registros rechazados en ventas:")
        for r in sales_result.rejected:
            print(f"   TX: {r['raw'].get('transaction_id')} → {r['reason'][:80]}")

    # 3. Persistir
    with Session(engine) as session:
        sales_inserted = persist_sales(session, sales_result)
        spend_inserted = persist_ad_spend(session, spend_result)
        refresh_campaign_performance(session)

    print(f"Insertados - Ventas: {sales_inserted} | Inversión: {spend_inserted}")
    print("Pipeline completado")

    return {
        "sales_generated": len(raw_sales),
        "sales_valid": len(sales_result.valid),
        "sales_rejected": len(sales_result.rejected),
        "sales_inserted": sales_inserted,
        "spend_generated": len(raw_spend),
        "spend_valid": len(spend_result.valid),
        "spend_rejected": len(spend_result.rejected),
        "spend_inserted": spend_inserted,
    }


if __name__ == "__main__":
    run_pipeline()
