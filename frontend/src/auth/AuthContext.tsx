import { createContext, useCallback, useContext, useState } from "react";
import { api, clearTokens, getUser, setTokens, User } from "../api/client";

interface AuthCtx {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({ user: null, login: async () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(getUser());

  const login = useCallback(async (email: string, password: string) => {
    const t = await api.login(email, password);
    setTokens(t);
    setUser(t.user);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);