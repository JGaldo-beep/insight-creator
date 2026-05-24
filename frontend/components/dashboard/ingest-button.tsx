"use client";

import { useState } from "react";
import { Database, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { triggerIngest } from "@/lib/api";
import type { IngestResponse } from "@/lib/types";

export type IngestButtonProps = {
  onSuccess?: () => void;
};

export function IngestButton({ onSuccess }: IngestButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<IngestResponse | null>(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await triggerIngest();
      setLast(res);
      onSuccess?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  const summary = last?.result
    ? `${last.result.sales_inserted ?? 0} ventas · ${last.result.spend_inserted ?? 0} spend`
    : null;

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        onClick={handleClick}
        disabled={loading}
        variant="default"
        size="sm"
        className="gap-2"
      >
        {loading ? (
          <Spinner />
        ) : last ? (
          <RefreshCw className="size-4" />
        ) : (
          <Database className="size-4" />
        )}
        {loading
          ? "Ingiriendo…"
          : last
            ? "Volver a ingerir"
            : "Disparar ingesta"}
      </Button>
      {summary && !error && (
        <span className="text-xs text-muted-foreground tabular-nums">
          {summary}
        </span>
      )}
      {error && (
        <span className="text-xs text-rose-600">{error}</span>
      )}
    </div>
  );
}
