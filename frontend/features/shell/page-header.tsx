import { ReactNode } from "react";

export function PageHeader({ title, eyebrow, children }: { title: string; eyebrow: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 border-b pb-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{eyebrow}</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground">{title}</h1>
      </div>
      {children}
    </div>
  );
}
