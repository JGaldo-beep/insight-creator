# Insight Extractor & History Tracker

Sistema full-stack de Ingeniería de Datos + IA: pipelines de gobernanza, agente
conversacional LangGraph y un dashboard en Next.js para análisis de campañas de
marketing.

## Stack Tecnológico

### Backend
- **Base de datos:** PostgreSQL 15
- **API:** Python 3.11, FastAPI, SQLAlchemy
- **IA:** LangChain, LangGraph, OpenAI GPT-4o-mini
- **Gobernanza:** Pydantic
- **Infraestructura:** Docker, Docker Compose
- **Gestor de paquetes:** [uv](https://docs.astral.sh/uv/)

### Frontend
- **Framework:** Next.js 16 (App Router) · React 19 · TypeScript
- **UI:** Tailwind CSS v4 · shadcn/ui · [Vercel AI Elements](https://elements.ai-sdk.dev)
- **Chat:** Vercel AI SDK v6 (streaming con `reasoning`, `tools` y `data parts`)
- **Charts:** Recharts
- **Gestor de paquetes:** pnpm

## Estructura del Proyecto

```text
insight-extractor/
├── src/                            # Backend Python
│   ├── data/
│   │   ├── models.py               # SQLAlchemy (tablas, SCD2, vistas)
│   │   ├── pipeline.py             # Ingesta, validación y persistencia
│   │   └── validator.py            # Reglas de gobernanza con Pydantic
│   ├── ai/
│   │   ├── agent.py                # Grafo LangGraph (classify → tools → reason)
│   │   └── tools.py                # Herramientas SQL del agente
│   └── main.py                     # API FastAPI
│
├── frontend/                       # Frontend Next.js 16
│   ├── app/
│   │   ├── page.tsx                # Dashboard (KPIs + charts)
│   │   ├── chat/page.tsx           # Chat con el agente
│   │   ├── api/chat/route.ts       # Proxy SSE → /chat del backend
│   │   ├── layout.tsx              # Shell + sidebar
│   │   └── globals.css             # Tema Tailwind v4 (light)
│   ├── components/
│   │   ├── ai-elements/            # Vercel AI Elements (Conversation, Tool, Reasoning…)
│   │   ├── ui/                     # shadcn/ui
│   │   ├── dashboard/              # KpiCard, charts, IngestButton
│   │   ├── chat/                   # FindingsList, RecommendationsList
│   │   └── sidebar-nav.tsx         # Sidebar + drawer mobile
│   ├── lib/
│   │   ├── api.ts                  # Helpers fetchMetrics / triggerIngest
│   │   ├── types.ts                # Tipos del backend + InsightMessage
│   │   └── utils.ts                # cn (tailwind-merge)
│   └── package.json
│
├── migrations/init_db.py           # Creación de tablas y vista de KPIs
├── tests/test_validator.py         # Tests de gobernanza
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── ARCHITECTURE.md
└── .env.example
```

## Requisitos Previos

- **Docker** + **Docker Compose** (backend)
- **Node.js 20+** y **pnpm 10+** (frontend) — `npm i -g pnpm`
- **uv** (opcional, para correr backend fuera de Docker) — `pip install uv`
- **API Key de OpenAI**

## Quickstart

### 1. Clona el repo y configura el `.env`

```bash
git clone <url-del-repo>
cd insight-extractor
cp .env.example .env
```

Edita `.env`:

```env
OPENAI_API_KEY=sk-tu-clave-aqui
DATABASE_URL=postgresql://insight_user:insight_pass@localhost:5432/insight_db
```

### 2. Backend — levanta Postgres + FastAPI

```bash
docker compose up --build
```

Esto orquesta en orden:
1. PostgreSQL → base de datos lista
2. Migraciones → tablas y vistas creadas
3. Seed → datos simulados insertados
4. API → corriendo en `http://localhost:8000` (docs en `/docs`)

### 3. Frontend — instala y arranca el dashboard

```bash
cd frontend
cp .env.example .env.local      # o crea uno con NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm install
pnpm dev
```

Abre `http://localhost:3000`:
- `/` — Dashboard con KPIs globales, ROI por canal y revenue vs ad spend.
- `/chat` — Chat con el agente (streaming, reasoning con shimmer "Pensando…", tools reales con input/output JSON, findings y recomendaciones).

> En mobile el sidebar se vuelve un drawer con hamburger en una top bar fija.

### Setup alternativo (sin Docker, solo backend)

Si quieres correr el backend nativo en lugar de Docker:

```bash
uv venv
uv pip install -r requirements.txt
# Necesitas Postgres corriendo aparte y DATABASE_URL apuntando a él
uv run python -m migrations.init_db
uv run uvicorn src.main:app --reload --port 8000
```

## Endpoints del Backend

| Método | Endpoint        | Descripción                                  |
|--------|-----------------|----------------------------------------------|
| `GET`  | `/`             | Health check                                 |
| `GET`  | `/metrics`      | KPIs actuales agregados desde la BD          |
| `POST` | `/data/ingest`  | Dispara el pipeline completo de ingesta      |
| `POST` | `/chat`         | Conversa con el agente IA (intent + tools + findings + recomendaciones) |

Documentación interactiva: `http://localhost:8000/docs`

### Ejemplos `curl`

```bash
# Métricas
curl http://localhost:8000/metrics

# Chat con el agente
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué canal tiene mejor ROI y qué recomendaciones tienes?"}'

# Disparar ingesta
curl -X POST http://localhost:8000/data/ingest
```

## Cómo se conectan frontend y backend

```mermaid
flowchart LR
    User[Browser :3000] --> Next[Next.js App Router]
    Next -->|GET /metrics<br/>POST /data/ingest| API[FastAPI :8000]
    Next -->|POST /api/chat<br/>SSE UI Message Stream| Route[app/api/chat/route.ts]
    Route -->|POST /chat<br/>JSON| API
    API --> Agent[LangGraph Agent]
    Agent --> DB[(PostgreSQL)]
```

- El dashboard llama directo al FastAPI (CORS abierto).
- El chat usa un route handler de Next.js que envuelve la respuesta JSON del agente
  en un **UI Message Stream** (SSE) para `useChat`, simulando streaming letra por
  letra y exponiendo `tool_calls` reales del agente como `dynamic-tool` parts.

## Gobernanza de Datos

El pipeline aplica las siguientes reglas antes de persistir:

| Regla                     | Ejemplo                                          |
|---------------------------|--------------------------------------------------|
| Homologación de canales   | `"fb ads"`, `"FB Ads"`, `"Facebook"` → `FACEBOOK`|
| Sin montos negativos      | `-100` → rechazado                               |
| Sin fechas futuras        | `2099-01-01` → rechazado                         |
| Deduplicación             | Mismo `transaction_id` → omitido                 |

## KPIs Calculados

- **ROI** — `(ingresos - inversión) / inversión`
- **CAC** — `inversión / clientes únicos`
- **Tasa de Conversión** — `transacciones / clics`

## Tests

```bash
# Backend
uv run pytest tests/ -v

# Frontend (typecheck + build)
cd frontend && pnpm build
```

## Documentación adicional

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — arquitectura local, propuesta de
  escalado a GCP (Cloud Run + Cloud SQL + BigQuery + Vertex AI) y pipeline de
  CI/CD en Azure DevOps.
