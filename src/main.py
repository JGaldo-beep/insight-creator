import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.data.pipeline import run_pipeline
from src.ai.agent import chat

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://insight_user:insight_pass@localhost:5432/insight_db"
)

engine = create_engine(DATABASE_URL)

app = FastAPI(
    title="Insight Extractor API",
    description="API para análisis de campañas de marketing con IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------
# Schemas
# ----------------------------------------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    summary: str
    findings: list[str]
    recommendations: list[str]
    natural_response: str


# ----------------------------------------
# Endpoints
# ----------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "Insight Extractor API corriendo"}


@app.post("/data/ingest")
def ingest():
    """Dispara el pipeline completo de ingesta y gobernanza."""
    try:
        result = run_pipeline()
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def get_metrics():
    """Devuelve KPIs actuales directo desde la base de datos."""
    try:
        with Session(engine) as session:
            kpis = session.execute(
                text("""
                    SELECT
                        channel_key,
                        ROUND(AVG(roi)::numeric, 4)             AS avg_roi,
                        ROUND(AVG(cac)::numeric, 2)             AS avg_cac,
                        ROUND(AVG(conversion_rate)::numeric, 4) AS avg_conversion_rate,
                        ROUND(SUM(total_revenue)::numeric, 2)   AS total_revenue,
                        ROUND(SUM(total_ad_spend)::numeric, 2)  AS total_ad_spend
                    FROM vw_kpis
                    GROUP BY channel_key
                    ORDER BY avg_roi DESC
                """)
            ).fetchall()

            global_summary = session.execute(
                text("""
                    SELECT
                        ROUND(SUM(total_revenue)::numeric, 2)  AS total_revenue,
                        ROUND(SUM(total_ad_spend)::numeric, 2) AS total_ad_spend,
                        ROUND(
                            (SUM(total_revenue) - SUM(total_ad_spend))
                            / NULLIF(SUM(total_ad_spend), 0)
                        , 4)                                    AS global_roi,
                        SUM(total_transactions)                 AS total_transactions
                    FROM fact_campaign_performance
                """)
            ).fetchone()

        return {
            "status": "success",
            "global": {
                "total_revenue": float(global_summary.total_revenue or 0),
                "total_ad_spend": float(global_summary.total_ad_spend or 0),
                "global_roi": float(global_summary.global_roi or 0),
                "total_transactions": int(global_summary.total_transactions or 0),
            },
            "by_channel": [
                {
                    "channel": row.channel_key,
                    "avg_roi": float(row.avg_roi or 0),
                    "avg_cac": float(row.avg_cac or 0),
                    "avg_conversion_rate": float(row.avg_conversion_rate or 0),
                    "total_revenue": float(row.total_revenue or 0),
                    "total_ad_spend": float(row.total_ad_spend or 0),
                }
                for row in kpis
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Interactúa con el agente de IA en lenguaje natural."""
    try:
        response = chat(request.message)
        return ChatResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
