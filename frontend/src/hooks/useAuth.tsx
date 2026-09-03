import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api, type AuthUser } from "../lib/api";

interface AuthState {
  user: AuthUser | null;
  status: "loading" | "authed" | "anon";
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");

  const refresh = useCallback(async () => {
    try {
      setUser(await api.auth.me());
      setStatus("authed");
    } catch (err) {
      setUser(null);
      // 401 -> auth is on and we're signed out. A network error also
      // lands here; showing the login form is the safe fallback.
      setStatus("anon");
      if (!(err instanceof ApiError)) {
        console.warn("auth check failed", err);
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setStatus("anon");
    };
    window.addEventListener("auth-expired", onExpired);
    return () => window.removeEventListener("auth-expired", onExpired);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const u = await api.auth.login(username, password);
    setUser(u);
    setStatus("authed");
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } finally {
      setUser(null);
      setStatus("anon");
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
