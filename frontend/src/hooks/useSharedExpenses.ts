import { useCallback, useEffect, useState } from "react";
import { api, type SharedExpenseOut } from "../lib/api";

export interface UseSharedExpensesResult {
  data: SharedExpenseOut[];
  loading: boolean;
  error: Error | null;
  refresh: () => void;
}

export function useSharedExpenses(): UseSharedExpensesResult {
  const [data, setData] = useState<SharedExpenseOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((value) => value + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const expenses = await api.getSharedExpenses();
        if (!cancelled) setData(expenses);
      } catch (error) {
        if (!cancelled) {
          // never keep rows from before a failure: a retry starts from a clean state
          setData([]);
          setError(error as Error);
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
