import * as React from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, variant = "default", ...props }: React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "outline" | "danger" | "warning" }) {
  const variants = {
    default: "bg-primary/10 text-primary",
    outline: "border bg-card text-muted-foreground",
    danger: "bg-red-50 text-red-700",
    warning: "bg-amber-50 text-amber-700"
  };
  return <div className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", variants[variant], className)} {...props} />;
}
