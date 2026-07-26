import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";

type AuthState = "checking" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  state: AuthState;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>("checking");

  useEffect(() => {
    api
      .get("/auth/me")
      .then(() => setState("authenticated"))
      .catch(() => setState("unauthenticated"));
  }, []);

  async function login(password: string) {
    await api.post("/auth/login", { password });
    setState("authenticated");
  }

  async function logout() {
    await api.post("/auth/logout");
    setState("unauthenticated");
  }

  return <AuthContext.Provider value={{ state, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
