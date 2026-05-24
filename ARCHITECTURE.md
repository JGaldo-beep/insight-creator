# Arquitectura y Escalabilidad

## Arquitectura Local (MVP)

El sistema actual corre completamente en Docker con cuatro servicios orquestados:

┌─────────────────────────────────────────────────────┐
│                  Docker Compose                     │
│                                                     │
│  ┌──────────┐    ┌────────────┐    ┌─────────────┐  │
│  │PostgreSQL│◄───│  FastAPI   │◄───│  LangGraph  │  │
│  │    db    │    │  :8000     │    │   Agent     │  │
│  └──────────┘    └────────────┘    └─────────────┘  │
│  ┌────┴───────┐                                     │
│  │  Pipeline  │                                     │
│  │  (Seed)    │                                     │
│  └────────────┘                                     │
│       ▲                                             │
└─────────────────────────────────────────────────────┘

## Arquitectura en GCP (Producción)

### Diagrama General

                    ┌─────────────────┐
                    │   Cloud Run     │
                    │   (FastAPI)     │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
 ┌────────▼───────┐ ┌───────▼──────┐ ┌────────▼────────┐
 │   Cloud SQL    │ │   BigQuery   │ │   Vertex AI     │
 │  (PostgreSQL)  │ │  (Analítico) │ │  (LLM/Agente)   │
 └────────────────┘ └──────────────┘ └─────────────────┘
          │                  │
 ┌────────▼───────┐ ┌───────▼──────┐
 │  Cloud Storage │ │     dbt      │
 │  (Raw Data)    │ │(Transforma.) │
 └────────────────┘ └──────────────┘

 ### Componentes y Justificación

#### Ingesta y Almacenamiento

**Cloud Storage (GCS)**
- Recibe los archivos crudos de las fuentes (CSV, JSON)
- Actúa como Data Lake - almacena el dato sin transformar
- Bajo costo y alta durabilidad para datos históricos

**Cloud SQL (PostgreSQL)**
- Reemplaza el PostgreSQL local del MVP
- Maneja las transacciones OLTP y el historial SCD2
- Se conecta a Cloud Run via Private IP para mayor seguridad

**BigQuery**
- Capa analítica OLAP para consultas de KPIs a escala
- Reemplaza la vista `vw_kpis` con tablas particionadas por fecha
- Permite consultas sobre miles de millones de registros sin degradar performance

#### Transformación y Gobernanza

**dbt (Data Build Tool)**
- Reemplaza y extiende el `pipeline.py` actual
- Define las transformaciones como SQL versionado en Git
- Genera documentación automática del linaje de datos
- Aplica tests de calidad nativos (not_null, unique, accepted_values)

GCS (raw) → dbt → BigQuery (curated) → vw_kpis → Agente

#### IA y Agente

**Vertex AI**
- Hospeda el agente LangGraph en producción
- Permite usar modelos de Google (Gemini) o modelos propios fine-tuned
- Escala automáticamente según demanda de consultas

**Cloud Run**
- Despliega la API FastAPI como contenedor serverless
- Escala a cero cuando no hay tráfico - costo optimizado
- Se conecta a Cloud SQL, BigQuery y Vertex AI via VPC

#### Seguridad

Cloud Run
│
├── Cloud SQL      → Usuario read-only para el agente
├── BigQuery       → IAM roles por servicio (principle of least privilege)
└── Secret Manager → API keys y credenciales (nunca en variables de entorno)

- El agente de IA mantiene permisos de solo lectura en producción
- Las credenciales se gestionan con **Google Secret Manager**
- La comunicación entre servicios usa **VPC privada**, nunca internet público

---

## Pipeline de CI/CD en Azure DevOps

### Flujo General

Developer → Git Push → Azure DevOps Pipeline
│
┌───────────────┼───────────────┐
│               │               │
Lint &          Tests          Build &
Format         (pytest)         Push
(ruff)                        (Docker)
│               │               │
└───────────────┼───────────────┘
│
┌─────────▼──────────┐
│  Deploy Staging    │
│  (Cloud Run dev)   │
└─────────┬──────────┘
│
┌─────────▼──────────┐
│  Approval Manual   │
│  (Tech Lead)       │
└─────────┬──────────┘
│
┌─────────▼──────────┐
│  Deploy Production │
│  (Cloud Run prod)  │
└────────────────────┘

### `azure-pipelines.yml`

```yaml
trigger:
  branches:
    include:
      - main
      - feat/*

stages:

  - stage: Quality
    displayName: Lint & Tests
    jobs:
      - job: lint_and_test
        pool:
          vmImage: ubuntu-latest
        steps:
          - script: pip install ruff pytest
            displayName: Instalar herramientas

          - script: ruff check src/
            displayName: Lint con ruff

          - script: pytest tests/ -v
            displayName: Correr tests

  - stage: Build
    displayName: Build & Push Docker
    dependsOn: Quality
    jobs:
      - job: docker_build
        steps:
          - task: Docker@2
            displayName: Build y push imagen
            inputs:
              containerRegistry: gcr-connection
              repository: insight-extractor
              command: buildAndPush
              tags: $(Build.BuildId)

  - stage: Staging
    displayName: Deploy Staging
    dependsOn: Build
    jobs:
      - job: deploy_staging
        steps:
          - script: |
              gcloud run deploy insight-extractor-staging \
                --image gcr.io/PROJECT_ID/insight-extractor:$(Build.BuildId) \
                --region us-central1 \
                --set-secrets OPENAI_API_KEY=openai-key:latest
            displayName: Deploy en Cloud Run Staging

  - stage: Production
    displayName: Deploy Production
    dependsOn: Staging
    # Requiere aprobación manual antes de continuar
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: deploy_prod
        environment: production
        strategy:
          runOnce:
            deploy:
              steps:
                - script: |
                    gcloud run deploy insight-extractor \
                      --image gcr.io/PROJECT_ID/insight-extractor:$(Build.BuildId) \
                      --region us-central1 \
                      --set-secrets OPENAI_API_KEY=openai-key:latest
                  displayName: Deploy en Cloud Run Production

                - script: |
                    python -m migrations.init_db
                  displayName: Correr migraciones de BD
```

### Estrategia de Migraciones

Las migraciones de base de datos siguen esta política:

- **Siempre aditivas** -> nunca eliminar columnas directamente, primero deprecar
- **Versionadas con Alembic** -> cada cambio de esquema tiene un script reversible
- **Se corren antes del deploy** -> si la migración falla, el deploy no continúa
- **Ambiente de staging primero** -> nunca migrar producción sin validar en staging

---

## Comparación MVP vs Producción

| Componente | MVP Local | Producción GCP |
|---|---|---|
| Base de datos | PostgreSQL (Docker) | Cloud SQL + BigQuery |
| API | FastAPI (uvicorn) | Cloud Run (serverless) |
| Agente IA | LangGraph + OpenAI | Vertex AI + Gemini |
| Transformaciones | pipeline.py | dbt |
| Secretos | .env file | Secret Manager |
| CI/CD | Manual | Azure DevOps |
| Monitoreo | Logs en consola | Cloud Monitoring + Alertas |
| Costo idle | Siempre encendido | Escala a cero |