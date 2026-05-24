"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  DollarSign,
  ShoppingCart,
  TrendingUp,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { RoiByChannelChart } from "@/components/dashboard/roi-by-channel-chart";
import { RevenueVsSpendChart } from "@/components/dashboard/revenue-vs-spend-chart";
import { IngestButton } from "@/components/dashboard/ingest-button";
import { fetchMetrics } from "@/lib/api";
import type { MetricsResponse } from "@/lib/types";

const currency = (v: number) =>
  v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

export default function DashboardPage() {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchMetrics();
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const g = data?.global;
  const roi = g?.global_roi ?? 0;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
      <header className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            KPIs de campañas de marketing en tiempo real
          </p>
        </div>
        <IngestButton onSuccess={load} />
      </header>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>No pudimos cargar las métricas</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-12">
          <Spinner />
          Cargando métricas…
        </div>
      )}

      {data && g && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              title="ROI Global"
              value={`${(roi * 100).toFixed(2)}%`}
              icon={TrendingUp}
              tone={roi >= 0 ? "positive" : "negative"}
              hint={roi >= 0 ? "Inversión rentable" : "Pérdida sobre inversión"}
            />
            <KpiCard
              title="Revenue Total"
              value={currency(g.total_revenue)}
              icon={DollarSign}
            />
            <KpiCard
              title="Ad Spend Total"
              value={currency(g.total_ad_spend)}
              icon={Activity}
            />
            <KpiCard
              title="Transacciones"
              value={g.total_transactions.toLocaleString("en-US")}
              icon={ShoppingCart}
            />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <RoiByChannelChart data={data.by_channel} />
            <RevenueVsSpendChart data={data.by_channel} />
          </div>
        </>
      )}
    </div>
  );
}
