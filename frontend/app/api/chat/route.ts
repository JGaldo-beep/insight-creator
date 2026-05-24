import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";
import type { ChatBackendResponse, InsightMessage } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

const INTENT_LABELS: Record<string, string> = {
  data_query: "consulta de datos",
  kpi_analysis: "análisis de KPIs",
  general: "pregunta general",
};

const TOOL_TITLES: Record<string, string> = {
  get_kpis: "Consultar KPIs por canal",
  get_channel_performance_summary: "Resumen de performance por canal",
  get_channel_trend: "Evolución temporal de un canal",
  get_period_summary: "Resumen global del período",
};

function extractUserText(msg: UIMessage): string {
  return msg.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("\n");
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  const userText = lastUser ? extractUserText(lastUser) : "";

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const stream = createUIMessageStream<InsightMessage>({
    execute: async ({ writer }) => {
      // 1. Reasoning visible inmediato — esto activa el shimmer "Thinking…"
      const reasoningId = "reasoning";
      writer.write({ type: "reasoning-start", id: reasoningId });
      writer.write({
        type: "reasoning-delta",
        id: reasoningId,
        delta: "Interpretando tu pregunta y decidiendo qué datos consultar…",
      });

      // 2. Llamada al backend (5-15s mientras el agente clasifica, ejecuta tools y razona)
      let data: ChatBackendResponse;
      try {
        const res = await fetch(`${apiUrl}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userText }),
        });
        if (!res.ok) throw new Error(`Backend respondió ${res.status}`);
        data = (await res.json()) as ChatBackendResponse;
      } catch (e) {
        writer.write({
          type: "reasoning-delta",
          id: reasoningId,
          delta: "\n\nNo pude contactar al backend.",
        });
        writer.write({ type: "reasoning-end", id: reasoningId });

        const errId = "err";
        writer.write({ type: "text-start", id: errId });
        writer.write({
          type: "text-delta",
          id: errId,
          delta: `Lo siento, no pude contactar al agente. Verifica que el backend esté corriendo en ${apiUrl}.`,
        });
        writer.write({ type: "text-end", id: errId });
        return;
      }

      // 3. Cerramos el reasoning con un resumen del flujo real
      const intentLabel = data.intent
        ? INTENT_LABELS[data.intent] ?? data.intent
        : null;
      if (intentLabel) {
        writer.write({
          type: "reasoning-delta",
          id: reasoningId,
          delta: `\n\nClasifiqué tu consulta como **${intentLabel}**.`,
        });
      }
      if (data.tool_calls?.length) {
        const names = data.tool_calls
          .map((t) => `\`${t.tool}\``)
          .join(", ");
        writer.write({
          type: "reasoning-delta",
          id: reasoningId,
          delta: `\n\nUsé ${data.tool_calls.length} herramienta(s) para responder: ${names}.`,
        });
      } else {
        writer.write({
          type: "reasoning-delta",
          id: reasoningId,
          delta: "\n\nNo necesité herramientas externas — respondí desde mi conocimiento.",
        });
      }
      writer.write({ type: "reasoning-end", id: reasoningId });

      // 4. Tools reales como dynamic tool parts (cada una con input + output)
      if (data.tool_calls?.length) {
        for (let i = 0; i < data.tool_calls.length; i++) {
          const tc = data.tool_calls[i];
          const callId = tc.tool_call_id || `tc-${i}`;
          const title = TOOL_TITLES[tc.tool] ?? tc.tool;

          writer.write({
            type: "tool-input-start",
            toolCallId: callId,
            toolName: tc.tool,
            dynamic: true,
            title,
          });
          writer.write({
            type: "tool-input-available",
            toolCallId: callId,
            toolName: tc.tool,
            input: tc.input ?? {},
            dynamic: true,
            title,
          });
          writer.write({
            type: "tool-output-available",
            toolCallId: callId,
            output: tc.output ?? null,
            dynamic: true,
          });
        }
      }

      // 5. Streaming del natural_response letra por letra
      const textId = "main";
      writer.write({ type: "text-start", id: textId });
      const text = data.natural_response ?? "";
      const chunkSize = 6;
      for (let i = 0; i < text.length; i += chunkSize) {
        writer.write({
          type: "text-delta",
          id: textId,
          delta: text.slice(i, i + chunkSize),
        });
        await sleep(20);
      }
      writer.write({ type: "text-end", id: textId });

      // 6. Findings y Recommendations como data parts persistentes
      if (data.findings?.length) {
        writer.write({
          type: "data-findings",
          id: "findings",
          data: { items: data.findings },
        });
      }
      if (data.recommendations?.length) {
        writer.write({
          type: "data-recommendations",
          id: "recommendations",
          data: { items: data.recommendations },
        });
      }
    },
  });

  return createUIMessageStreamResponse({ stream });
}
