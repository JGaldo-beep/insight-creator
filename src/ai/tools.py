import os
from datetime import date
from decimal import Decimal
from typing import Optional
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from langchain_core.tools import tool

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://insight_user:insight_pass@localhost:5432/insight_db"
)

engine = create_engine(DATABASE_URL)


def _serialize(value):
    """Convierte tipos no serializables a string para el agente."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _rows_to_dict(rows) -> list[dict]:
    """Convierte resultados de SQLAlchemy a lista de dicts."""
    return [
        {key: _serialize(value) for key, value in row._mapping.items()} for row in rows
    ]


# ---------------------------------------------
# Tool 1: KPIs generales
# ---------------------------------------------
@tool
def get_kpis(channel: Optional[str] = None, limit: int = 30) -> list[dict]:
    """
    Obtiene los KPIs calculados (ROI, CAC, tasa de conversión)
    desde la vista vw_kpis. Opcionalmente filtra por canal.
    """
    with Session(engine) as session:
        if channel:
            rows = session.execute(
                text("""
                    SELECT *
                    FROM vw_kpis
                    WHERE channel_key = :channel
                    ORDER BY perf_date DESC
                    LIMIT :limit
                """),
                {"channel": channel.upper(), "limit": limit},
            ).fetchall()
        else:
            rows = session.execute(
                text("""
                    SELECT *
                    FROM vw_kpis
                    ORDER BY perf_date DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()

    return _rows_to_dict(rows)


# ---------------------------------------------
# Tool 2: Mejor y peor canal por ROI
# ---------------------------------------------
@tool
def get_channel_performance_summary() -> list[dict]:
    """
    Devuelve un resumen por canal con ROI promedio, inversión total
    e ingresos totales. Útil para comparar canales entre sí.
    """
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT
                    channel_key,
                    ROUND(AVG(roi)::numeric, 4)              AS avg_roi,
                    ROUND(AVG(cac)::numeric, 2)              AS avg_cac,
                    ROUND(AVG(conversion_rate)::numeric, 4)  AS avg_conversion_rate,
                    ROUND(SUM(total_revenue)::numeric, 2)    AS total_revenue,
                    ROUND(SUM(total_ad_spend)::numeric, 2)   AS total_ad_spend,
                    COUNT(*)                                  AS days_active
                FROM vw_kpis
                WHERE roi IS NOT NULL
                GROUP BY channel_key
                ORDER BY avg_roi DESC
            """)
        ).fetchall()

    return _rows_to_dict(rows)


# ---------------------------------------------
# Tool 3: Tendencia temporal de un canal
# ---------------------------------------------
@tool
def get_channel_trend(channel: str, days: int = 14) -> list[dict]:
    """
    Devuelve la evolución diaria de ROI, ingresos e inversión
    de un canal específico en los últimos N días.
    """
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT
                    perf_date,
                    channel_key,
                    total_revenue,
                    total_ad_spend,
                    roi,
                    cac,
                    conversion_rate
                FROM vw_kpis
                WHERE channel_key = :channel
                  AND perf_date >= CURRENT_DATE - :days * INTERVAL '1 day'
                ORDER BY perf_date ASC
            """),
            {"channel": channel.upper(), "days": days},
        ).fetchall()

    return _rows_to_dict(rows)


# ----------------------------------------------
# Tool 4: Resumen general del período
# ----------------------------------------------
@tool
def get_period_summary(days: int = 30) -> dict:
    """
    Devuelve métricas agregadas del período: ingresos totales,
    inversión total, ROI global y canal con mejor desempeño.
    """
    with Session(engine) as session:
        row = session.execute(
            text("""
                SELECT
                    ROUND(SUM(total_revenue)::numeric, 2)   AS total_revenue,
                    ROUND(SUM(total_ad_spend)::numeric, 2)  AS total_ad_spend,
                    ROUND(
                        (SUM(total_revenue) - SUM(total_ad_spend))
                        / NULLIF(SUM(total_ad_spend), 0)
                    , 4)                                     AS global_roi,
                    SUM(total_transactions)                  AS total_transactions,
                    SUM(unique_customers)                    AS total_unique_customers
                FROM fact_campaign_performance
                WHERE perf_date >= CURRENT_DATE - :days * INTERVAL '1 day'
            """),
            {"days": days},
        ).fetchone()

        best_channel = session.execute(
            text("""
                SELECT channel_key, ROUND(AVG(roi)::numeric, 4) AS avg_roi
                FROM vw_kpis
                WHERE perf_date >= CURRENT_DATE - :days * INTERVAL '1 day'
                  AND roi IS NOT NULL
                GROUP BY channel_key
                ORDER BY avg_roi DESC
                LIMIT 1
            """),
            {"days": days},
        ).fetchone()

    return {
        **{key: _serialize(value) for key, value in row._mapping.items()},
        "best_channel": best_channel.channel_key if best_channel else None,
        "best_channel_roi": _serialize(best_channel.avg_roi) if best_channel else None,
        "period_days": days,
    }
