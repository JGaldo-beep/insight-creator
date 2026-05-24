import type { IngestResponse, MetricsResponse } from "@/lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchMetrics(): Promise<MetricsResponse> {
  const res = await fetch(`${API_URL}/metrics`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch metrics: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function triggerIngest(): Promise<IngestResponse> {
  const res = await fetch(`${API_URL}/data/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger ingest: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
