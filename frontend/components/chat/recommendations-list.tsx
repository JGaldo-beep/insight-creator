import { CheckCircle2, Sparkles } from "lucide-react";

export type RecommendationsListProps = {
  items: string[];
};

export function RecommendationsList({ items }: RecommendationsListProps) {
  if (!items?.length) return null;
  return (
    <div className="mt-3 rounded-lg border border-border/70 bg-emerald-50/40 p-4">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-emerald-700/80">
        <Sparkles className="size-3.5" />
        Recomendaciones
      </div>
      <ul className="space-y-2 text-sm">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-foreground/90">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
