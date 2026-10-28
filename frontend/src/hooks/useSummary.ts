import { useCallback, useEffect, useState } from "react";
import { api, type SummaryOut } from "../lib/api";

export interface UseSummaryResult {
  data: SummaryOut | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
}

export function useSummary(): UseSummaryResult {
  const [data, setData] = useState<SummaryOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const res = await api.getSummary();
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) {
          // never keep a balance from before a failure: a retry starts from a clean state
          setData(null);
          setError(e as Error);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tick]);

  return { data, loading, error, refresh };
}
