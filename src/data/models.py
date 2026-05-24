from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# -----------------------------------------------
# DIM: Catálogo de canales con historial (SCD2)
# -----------------------------------------------
class DimChannel(Base):
    """
    Slowly Changing Dimension Type 2.
    Cada vez que cambia el costo base de un canal,
    se cierra el registro actual y se crea uno nuevo.
    El pasado nunca se sobreescribe.
    """

    __tablename__ = "dim_channel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_key = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    base_cpc = Column(Numeric(10, 4), nullable=True)

    # Columnas SCD2
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_dim_channel_key", "channel_key"),
        Index("ix_dim_channel_current", "channel_key", "is_current"),
    )


# ----------------------------------------------
# FACT: Ventas diarias — Fuente A
# ----------------------------------------------
class FactSales(Base):
    """
    Datos crudos de ventas transaccionales.
    Un registro por transacción individual.
    """

    __tablename__ = "fact_sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), nullable=False, unique=True)
    customer_id = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    sale_date = Column(Date, nullable=False)
    channel_key = Column(String(50), nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("ix_fact_sales_date_channel", "sale_date", "channel_key"),)


# -----------------------------------------------
# FACT: Inversión publicitaria — Fuente B
# -----------------------------------------------
class FactAdSpend(Base):
    """
    Datos de inversión publicitaria por día y canal.
    Un registro por (fecha, canal) — se deduplica por esa combinación.
    """

    __tablename__ = "fact_ad_spend"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spend_date = Column(Date, nullable=False)
    channel_key = Column(String(50), nullable=False)
    cost = Column(Numeric(12, 2), nullable=False)
    impressions = Column(Integer, nullable=False)
    clicks = Column(Integer, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("spend_date", "channel_key", name="uq_adspend_date_channel"),
        Index("ix_fact_adspend_date_channel", "spend_date", "channel_key"),
    )


# ------------------------------------------------
# FACT: Tabla consolidada — la central del sistema
# ------------------------------------------------
class FactCampaignPerformance(Base):
    """
    Une ventas + inversión por día y canal.
    Es la tabla que consulta el agente de IA.
    Se actualiza con cada ingesta.
    """

    __tablename__ = "fact_campaign_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    perf_date = Column(Date, nullable=False)
    channel_key = Column(String(50), nullable=False)

    # Métricas de ventas
    total_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    total_transactions = Column(Integer, nullable=False, default=0)
    unique_customers = Column(Integer, nullable=False, default=0)

    # Métricas de inversión
    total_ad_spend = Column(Numeric(14, 2), nullable=False, default=0)
    total_impressions = Column(Integer, nullable=False, default=0)
    total_clicks = Column(Integer, nullable=False, default=0)

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("perf_date", "channel_key", name="uq_perf_date_channel"),
        Index("ix_perf_date_channel", "perf_date", "channel_key"),
    )
