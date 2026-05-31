"use client";

import { useEffect, useState } from "react";
import type { DependencyList } from "react";

import { currentOrgId } from "@/services/api";

export function useResource<T>(loader: () => Promise<T>, deps: DependencyList = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        if (!currentOrgId()) {
          throw new Error("No active demo session. Choose a startup or freelancer login first.");
        }
        const result = await loader();
        if (alive) setData(result);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        if (alive) setLoading(false);
      }
    }
    run();
    return () => {
      alive = false;
    };
  }, deps);

  return { data, error, loading, setData };
}
