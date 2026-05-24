"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { FindingsList } from "@/components/chat/findings-list";
import { RecommendationsList } from "@/components/chat/recommendations-list";
import type { InsightMessage } from "@/lib/types";

const STARTER_SUGGESTIONS = [
  "¿Qué canal tiene el mejor ROI?",
  "Recomienda dónde reasignar el ad spend",
  "Analiza la conversión por canal",
  "¿Cuál es el CAC promedio?",
];

const renderThinking = (isStreaming: boolean, duration?: number) => {
  if (isStreaming || duration === 0) {
    return <Shimmer duration={1}>Pensando…</Shimmer>;
  }
  if (duration === undefined) {
    return <span>Pensé por unos segundos</span>;
  }
  return <span>Pensé por {duration} segundos</span>;
};

export default function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status, stop } = useChat<InsightMessage>({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
  });

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    sendMessage({ text: trimmed });
    setInput("");
  };

  const handleSubmit = (message: PromptInputMessage) => {
    send(message.text);
  };

  return (
    <div className="mx-auto flex h-[calc(100dvh-3.5rem)] md:h-screen max-w-3xl flex-col px-4 py-6 md:px-6">
      <header className="mb-2">
        <h1 className="text-xl font-semibold tracking-tight">
          Chat con Insight Agent
        </h1>
        <p className="text-sm text-muted-foreground">
          Pregúntale al agente sobre el desempeño de tus campañas
        </p>
      </header>

      <Conversation className="flex-1">
        <ConversationContent>
          {messages.length === 0 ? (
            <ConversationEmptyState
              icon={<Sparkles className="size-10" />}
              title="Empieza una conversación"
              description="Tu agente analiza ROI, CAC y conversión en tiempo real"
            />
          ) : (
            messages.map((message, msgIdx) => {
              const isLast = msgIdx === messages.length - 1;
              return (
                <Message from={message.role} key={message.id}>
                  <MessageContent>
                    {message.parts.map((part, i) => {
                      const partKey = `${message.id}-${i}`;

                      if (part.type === "reasoning") {
                        const partStreaming =
                          part.state === "streaming" ||
                          (isLast &&
                            status === "streaming" &&
                            part.state !== "done");
                        return (
                          <Reasoning
                            key={partKey}
                            isStreaming={partStreaming}
                            defaultOpen
                          >
                            <ReasoningTrigger
                              getThinkingMessage={renderThinking}
                            />
                            <ReasoningContent>{part.text}</ReasoningContent>
                          </Reasoning>
                        );
                      }

                      if (part.type === "dynamic-tool") {
                        return (
                          <Tool key={partKey} defaultOpen={false}>
                            <ToolHeader
                              type="dynamic-tool"
                              state={part.state}
                              toolName={part.toolName}
                            />
                            <ToolContent>
                              {part.state !== "input-streaming" && (
                                <ToolInput input={part.input} />
                              )}
                              {(part.state === "output-available" ||
                                part.state === "output-error") && (
                                <ToolOutput
                                  output={
                                    part.state === "output-available"
                                      ? part.output
                                      : undefined
                                  }
                                  errorText={
                                    part.state === "output-error"
                                      ? part.errorText
                                      : undefined
                                  }
                                />
                              )}
                            </ToolContent>
                          </Tool>
                        );
                      }

                      if (part.type === "text") {
                        return (
                          <MessageResponse key={partKey}>
                            {part.text}
                          </MessageResponse>
                        );
                      }

                      if (part.type === "data-findings") {
                        return (
                          <FindingsList key={partKey} items={part.data.items} />
                        );
                      }

                      if (part.type === "data-recommendations") {
                        return (
                          <RecommendationsList
                            key={partKey}
                            items={part.data.items}
                          />
                        );
                      }

                      return null;
                    })}
                  </MessageContent>
                </Message>
              );
            })
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      {messages.length === 0 && (
        <Suggestions className="mb-3">
          {STARTER_SUGGESTIONS.map((s) => (
            <Suggestion key={s} suggestion={s} onClick={send} />
          ))}
        </Suggestions>
      )}

      <PromptInput onSubmit={handleSubmit} className="mt-2">
        <PromptInputBody>
          <PromptInputTextarea
            value={input}
            placeholder="Pregunta lo que quieras…"
            onChange={(e) => setInput(e.currentTarget.value)}
          />
        </PromptInputBody>
        <PromptInputFooter>
          <div className="flex-1" />
          <PromptInputSubmit
            status={status}
            onStop={stop}
            disabled={!input.trim() && status !== "streaming"}
          />
        </PromptInputFooter>
      </PromptInput>
    </div>
  );
}
