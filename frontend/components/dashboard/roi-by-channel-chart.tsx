"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ChannelMetrics } from "@/lib/types";

export type RoiByChannelChartProps = {
  data: ChannelMetrics[];
};

export function RoiByChannelChart({ data }: RoiByChannelChartProps) {
  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader>
        <CardTitle className="text-base font-semibold tracking-tight">
          ROI por canal
        </CardTitle>
        <CardDescription>Retorno promedio por cada peso invertido</CardDescription>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              vertical={false}
            />
            <XAxis
              dataKey="channel"
              stroke="var(--muted-foreground)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="var(--muted-foreground)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${v.toFixed(1)}x`}
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.4 }}
              contentStyle={{
                background: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                fontSize: 12,
              }}
              formatter={(value) => {
                const n = typeof value === "number" ? value : Number(value);
                return [`${n.toFixed(2)}x`, "ROI"];
              }}
            />
            <Bar
              dataKey="avg_roi"
              fill="var(--chart-3)"
              radius={[6, 6, 0, 0]}
              maxBarSize={64}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
