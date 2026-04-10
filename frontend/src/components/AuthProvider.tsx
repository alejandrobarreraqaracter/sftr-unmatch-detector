import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getMe, getStoredDemoUser, loginDemoUser, setStoredDemoUser, type DemoUser } from "@/lib/api";

type AuthContextValue = {
  user: DemoUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(getStoredDemoUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      const stored = getStoredDemoUser();
      if (!stored) {
        setLoading(false);
        return;
      }

      try {
        const me = await getMe();
        setUser(me);
        setStoredDemoUser(me);
      } catch {
        setUser(null);
        setStoredDemoUser(null);
      } finally {
        setLoading(false);
      }
    };
    void bootstrap();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(username: string, password: string) {
        const loggedIn = await loginDemoUser(username, password);
        setStoredDemoUser(loggedIn);
        setUser(loggedIn);
      },
      logout() {
        setStoredDemoUser(null);
        setUser(null);
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
