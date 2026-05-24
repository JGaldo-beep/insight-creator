import { Lightbulb } from "lucide-react";

export type FindingsListProps = {
  items: string[];
};

export function FindingsList({ items }: FindingsListProps) {
  if (!items?.length) return null;
  return (
    <div className="mt-3 rounded-lg border border-border/70 bg-muted/30 p-4">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <Lightbulb className="size-3.5" />
        Hallazgos
      </div>
      <ul className="space-y-1.5 text-sm">
        {items.map((item, i) => (
          <li
            key={i}
            className="relative pl-4 text-foreground/90 before:absolute before:left-0 before:top-[0.55em] before:size-1.5 before:rounded-full before:bg-muted-foreground/60"
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
