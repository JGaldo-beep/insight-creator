import type { UIMessage } from "ai";

export type ChannelMetrics = {
  channel: string;
  avg_roi: number;
  avg_cac: number;
  avg_conversion_rate: number;
  total_revenue: number;
  total_ad_spend: number;
};

export type GlobalMetrics = {
  total_revenue: number;
  total_ad_spend: number;
  global_roi: number;
  total_transactions: number;
};

export type MetricsResponse = {
  status: string;
  global: GlobalMetrics;
  by_channel: ChannelMetrics[];
};

export type IngestResponse = {
  status: string;
  result: Record<string, number>;
};

export type AgentToolCall = {
  tool: string;
  tool_call_id?: string | null;
  input?: Record<string, unknown> | null;
  output?: unknown;
};

export type ChatBackendResponse = {
  summary: string;
  findings: string[];
  recommendations: string[];
  natural_response: string;
  intent?: string | null;
  tool_calls?: AgentToolCall[];
};

export type InsightMessage = UIMessage<
  never,
  {
    findings: { items: string[] };
    recommendations: { items: string[] };
  }
>;
