import os
import json
from typing import TypedDict, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.ai.tools import (
    get_kpis,
    get_channel_performance_summary,
    get_channel_trend,
    get_period_summary,
)

load_dotenv()

# --------------------------------------
# Modelo LLM
# --------------------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Lista de tools disponibles para el agente
TOOLS = [
    get_kpis,
    get_channel_performance_summary,
    get_channel_trend,
    get_period_summary,
]

llm_with_tools = llm.bind_tools(TOOLS)


# --------------------------------------
# Estado del agente
# --------------------------------------
class AgentState(TypedDict):
    messages: list
    intent: Optional[str]
    query_results: Optional[list | dict]
    final_response: Optional[dict]


# --------------------------------------
# Nodo 1: Clasificador de intención
# --------------------------------------
def classify_node(state: AgentState) -> AgentState:
    """
    Determina qué tipo de solicitud es:
    - data_query: quiere números específicos
    - kpi_analysis: quiere análisis y recomendaciones
    - general: pregunta general sobre el sistema
    """
    last_message = state["messages"][-1].content

    system_prompt = """Eres un clasificador de intenciones para un sistema de análisis de marketing.
    
Clasifica la consulta del usuario en UNA de estas categorías:
- data_query: El usuario quiere datos específicos (ventas, inversión, métricas puntuales)
- kpi_analysis: El usuario quiere análisis, comparaciones, tendencias o recomendaciones estratégicas
- general: Pregunta general que no requiere consultar la base de datos

Responde ÚNICAMENTE con una de estas palabras: data_query, kpi_analysis, general"""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message),
        ]
    )

    # fallback por si el LLM no responde con una categoría clara
    intent = response.content.strip().lower()
    if intent not in ["data_query", "kpi_analysis", "general"]:
        intent = "kpi_analysis"

    print(f"Intención clasificada: {intent}")
    return {**state, "intent": intent}


# --------------------------------------
# Nodo 2: Ejecutor de consultas
# --------------------------------------
def execute_query_node(state: AgentState) -> AgentState:
    """
    El agente decide qué tool usar y la ejecuta.
    El LLM elige la tool correcta basado en la pregunta.
    """
    last_message = state["messages"][-1].content

    system_prompt = """Eres un analista de datos experto. Tienes acceso a herramientas 
para consultar una base de datos de campañas de marketing y ventas.

Herramientas disponibles:
- get_kpis: KPIs por fecha y canal (ROI, CAC, conversión)
- get_channel_performance_summary: Resumen comparativo de todos los canales
- get_channel_trend: Evolución temporal de un canal específico
- get_period_summary: Resumen global del período

IMPORTANTE:
- Solo puedes LEER datos, nunca modificarlos
- Usa la herramienta más específica para la pregunta
- Si la pregunta menciona un canal específico, filtra por ese canal
- Siempre llama al menos una herramienta antes de responder"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=last_message),
    ]

    response = llm_with_tools.invoke(messages)

    # Ejecutar las tools que el LLM decidió usar
    query_results = []
    if response.tool_calls:
        tool_node = ToolNode(TOOLS)
        tool_results = tool_node.invoke({"messages": [response]})

        # Mapeamos cada tool_call_id a los args originales para conservar los inputs
        args_by_id = {tc["id"]: tc.get("args", {}) for tc in response.tool_calls}
        name_by_id = {tc["id"]: tc.get("name") for tc in response.tool_calls}

        for msg in tool_results["messages"]:
            try:
                output = json.loads(msg.content)
            except (json.JSONDecodeError, AttributeError, TypeError):
                output = getattr(msg, "content", None)

            tool_call_id = getattr(msg, "tool_call_id", None)
            tool_name = getattr(msg, "name", None) or name_by_id.get(tool_call_id, "unknown")
            query_results.append(
                {
                    "tool": tool_name,
                    "tool_call_id": tool_call_id,
                    "input": args_by_id.get(tool_call_id, {}),
                    "output": output,
                }
            )

    print(f"Tools ejecutadas: {[r['tool'] for r in query_results]}")
    return {**state, "query_results": query_results}


# -------------------------------------------
# Nodo 3: Razonador y generador de respuesta
# -------------------------------------------
def reason_node(state: AgentState) -> AgentState:
    """
    Toma los datos obtenidos y genera un análisis
    con diagnóstico y recomendaciones de negocio.
    """
    last_message = state["messages"][-1].content
    query_results = state.get("query_results", [])

    system_prompt = """Eres un consultor senior de marketing digital y análisis de datos.

Tu trabajo es analizar los datos de campañas y dar recomendaciones accionables.

REGLAS:
1. No solo reportes números - diagnostica el POR QUÉ y recomienda QUÉ HACER
2. Usa lenguaje claro orientado a negocio, no técnico
3. Si el ROI es negativo, explica el impacto y sugiere acciones concretas
4. Compara canales cuando sea relevante
5. Sé específico con porcentajes y montos cuando los tengas

FORMATO DE RESPUESTA - responde SIEMPRE en este JSON:
{
    "summary": "Resumen ejecutivo en 2-3 oraciones",
    "findings": ["hallazgo 1", "hallazgo 2", "hallazgo 3"],
    "recommendations": ["recomendación concreta 1", "recomendación concreta 2"],
    "natural_response": "Respuesta completa en lenguaje natural para el usuario"
}"""

    data_context = json.dumps(query_results, ensure_ascii=False, indent=2)

    user_prompt = f"""Pregunta del usuario: {last_message}

Datos obtenidos de la base de datos:
{data_context}

Genera tu análisis siguiendo el formato JSON indicado."""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    # Parsear respuesta JSON
    try:
        clean = response.content.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        final_response = json.loads(clean)
    except json.JSONDecodeError:
        final_response = {
            "summary": "Análisis completado",
            "findings": [],
            "recommendations": [],
            "natural_response": response.content,
        }

    print("Respuesta generada")
    return {**state, "final_response": final_response}


# -------------------------------------------------
# Nodo para preguntas generales (sin BD)
# -------------------------------------------------
def general_node(state: AgentState) -> AgentState:
    """Responde preguntas generales sin consultar la BD."""
    last_message = state["messages"][-1].content

    response = llm.invoke(
        [
            SystemMessage(
                content="Eres un asistente de análisis de marketing. Responde de forma concisa."
            ),
            HumanMessage(content=last_message),
        ]
    )

    final_response = {
        "summary": "Respuesta general",
        "findings": [],
        "recommendations": [],
        "natural_response": response.content,
    }

    return {**state, "final_response": final_response}


# -------------------------------------------------
# Router -> decide el camino según la intención
# -------------------------------------------------
def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "kpi_analysis")
    if intent == "general":
        return "general"
    return "execute_query"


# -------------------------------------------------
# Construcción del grafo
# -------------------------------------------------
def build_agent():
    graph = StateGraph(AgentState)

    # Agregar nodos
    graph.add_node("classify", classify_node)
    graph.add_node("execute_query", execute_query_node)
    graph.add_node("reason", reason_node)
    graph.add_node("general", general_node)

    # Nodo de entrada
    graph.set_entry_point("classify")

    # Edges condicionales desde classify
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "execute_query": "execute_query",
            "general": "general",
        },
    )

    # Edges fijos
    graph.add_edge("execute_query", "reason")
    graph.add_edge("reason", END)
    graph.add_edge("general", END)

    return graph.compile()


# Instancia global del agente
agent = build_agent()


# -------------------------------------------
# Función pública para invocar el agente
# -------------------------------------------
def chat(user_message: str) -> dict:
    """Punto de entrada para interactuar con el agente."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "intent": None,
        "query_results": None,
        "final_response": None,
    }

    result = agent.invoke(initial_state)
    final = result["final_response"] or {}
    return {
        **final,
        "intent": result.get("intent"),
        "tool_calls": result.get("query_results") or [],
    }
