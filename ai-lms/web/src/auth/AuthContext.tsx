import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, api, setUnauthorisedHandler } from "../api/client";
import type { AppConfig, User } from "../api/types";

interface AuthState {
  /** True until the first /config and /me answers have arrived. */
  loading: boolean;
  /** Set when the server could not be reached at start-up. */
  startError: string | null;
  config: AppConfig | null;
  user: User | null;
  setUser: (user: User | null) => void;
  signOut: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [startError, setStartError] = useState<string | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setStartError(null);

    const me = api.me().catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 401) return null;
      throw error;
    });

    Promise.all([api.config(), me])
      .then(([loadedConfig, loadedUser]) => {
        if (cancelled) return;
        setConfig(loadedConfig);
        setUser(loadedUser);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setStartError(error instanceof Error ? error.message : "Could not start the app.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  // A 401 on any later request means the session has ended: back to sign-in.
  useEffect(() => {
    setUnauthorisedHandler(() => setUser(null));
    return () => setUnauthorisedHandler(null);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  const value = useMemo<AuthState>(
    () => ({ loading, startError, config, user, setUser, signOut, retry }),
    [loading, startError, config, user, signOut, retry],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth must be used inside AuthProvider");
  return state;
}
