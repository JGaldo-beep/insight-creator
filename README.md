# Insight Extractor & History Tracker

Sistema híbrido de Ingeniería de Datos e IA que combina pipelines de gobernanza
de datos con un agente conversacional inteligente para análisis de campañas de marketing.

## Stack Tecnológico

- **Base de datos:** PostgreSQL 15
- **Backend:** Python 3.11, FastAPI, SQLAlchemy
- **IA:** LangChain, LangGraph, OpenAI GPT-4o-mini
- **Gobernanza:** Pydantic
- **Infraestructura:** Docker, Docker Compose

## Estructura del Proyecto

insight-extractor/

├── src/

│   ├── data/

│   │   ├── models.py       # Modelos SQLAlchemy (tablas, SCD2, vistas)

│   │   ├── pipeline.py     # Ingesta, validación y persistencia

│   │   └── validator.py    # Reglas de gobernanza con Pydantic

│   ├── ai/

│   │   ├── agent.py        # Grafo LangGraph con 3 nodos

│   │   └── tools.py        # Herramientas de consulta SQL para el agente

│   └── main.py             # API FastAPI

├── migrations/

│   └── init_db.py          # Creación de tablas y vista de KPIs

├── tests/

│   └── test_validator.py   # Tests de gobernanza

├── Dockerfile

├── docker-compose.yml

├── requirements.txt

└── .env.example


## Requisitos Previos

- Docker y Docker Compose instalados
- API Key de OpenAI

## Instalación y Ejecución Local

### 1. Clona el repositorio

```bash
git clone <url-del-repo>
cd insight-extractor
```

### 2. Configura las variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y agrega tu API key:

```env
OPENAI_API_KEY=sk-tu-clave-aqui
DATABASE_URL=postgresql://insight_user:insight_pass@localhost:5432/insight_db
```

### 3. Levanta todo con Docker

```bash
docker-compose up --build
```

Esto ejecuta automáticamente en orden:
1. PostgreSQL -> base de datos lista
2. Migraciones -> tablas y vistas creadas
3. Seed -> datos simulados insertados
4. API -> servidor corriendo en `http://localhost:8000`

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/metrics` | KPIs actuales desde la BD |
| `POST` | `/data/ingest` | Dispara el pipeline de ingesta |
| `POST` | `/chat` | Conversa con el agente de IA |

Documentación interactiva disponible en `http://localhost:8000/docs`

## Ejemplos de Uso

### Consultar métricas

```bash
curl http://localhost:8000/metrics
```

### Chatear con el agente

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué canal tiene mejor ROI y qué recomendaciones tienes?"}'
```

### Disparar ingesta

```bash
curl -X POST http://localhost:8000/data/ingest
```

## Gobernanza de Datos

El pipeline aplica las siguientes reglas antes de persistir cualquier dato:

| Regla | Ejemplo |
|-------|---------|
| Homologación de canales | `"fb ads"`, `"FB Ads"`, `"Facebook"` → `FACEBOOK` |
| Sin montos negativos | `-100` → rechazado |
| Sin fechas futuras | `2099-01-01` → rechazado |
| Deduplicación | Mismo `transaction_id` → omitido |

## KPIs Calculados

- **ROI** - `(ingresos - inversión) / inversión`
- **CAC** - `inversión / clientes únicos`
- **Tasa de Conversión** - `transacciones / clics`

## Tests

```bash
uv run pytest tests/ -v
```
