import os
from sqlalchemy import create_engine, text
from src.data.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://insight_user:insight_pass@localhost:5432/insight_db")

def run():
    engine = create_engine(DATABASE_URL)

    Base.metadata.create_all(engine)
    print("Tablas creadas")

    # Crea la vista de KPIs -> SQL puro porque SQLAlchemy no tiene vistas nativas
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE OR REPLACE VIEW vw_kpis AS
            SELECT
                perf_date,
                channel_key,
                total_revenue,
                total_ad_spend,
                total_transactions,
                total_clicks,

                -- ROI: (ingresos - inversión) / inversión
                CASE
                    WHEN total_ad_spend > 0
                    THEN ROUND((total_revenue - total_ad_spend) / total_ad_spend, 4)
                    ELSE NULL
                END AS roi,

                -- CAC: inversión / clientes únicos
                CASE
                    WHEN unique_customers > 0
                    THEN ROUND(total_ad_spend / unique_customers, 2)
                    ELSE NULL
                END AS cac,

                -- Tasa de conversión: transacciones / clics
                CASE
                    WHEN total_clicks > 0
                    THEN ROUND(total_transactions::numeric / total_clicks, 4)
                    ELSE NULL
                END AS conversion_rate

            FROM fact_campaign_performance;
        """))
        conn.commit()
        print("Vista vw_kpis creada")

if __name__ == "__main__":
    run()