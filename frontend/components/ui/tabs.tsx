"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

export function SegmentedControl<T extends string>({
  value,
  onChange,
  items
}: {
  value: T;
  onChange: (value: T) => void;
  items: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex rounded-md border bg-card p-1">
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            "rounded px-3 py-1.5 text-sm font-medium text-muted-foreground transition",
            value === item.value && "bg-primary text-primary-foreground"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
