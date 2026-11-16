import { useEffect, useState, type DependencyList } from "react";
import { ApiError } from "../api/client";

interface AsyncState<T> {
  loading: boolean;
  data: T | null;
  error: string | null;
  /** HTTP status of a failed request, when there was one. */
  status: number | null;
}

/** Runs a request when the dependencies change and ignores answers that arrive too late. */
export function useAsync<T>(load: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ loading: true, data: null, error: null, status: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, data: null, error: null, status: null });
    load()
      .then((data) => {
        if (!cancelled) setState({ loading: false, data, error: null, status: null });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState({
          loading: false,
          data: null,
          error: error instanceof Error ? error.message : "Something went wrong.",
          status: error instanceof ApiError ? error.status : null,
        });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
