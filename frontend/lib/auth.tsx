"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { AuthStatus, clearLegacyTokenStorage, getAuthStatus, login as apiLogin, logout as apiLogout } from "@/lib/api";

interface AuthContextValue {
  status: AuthStatus | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    try {
      const next = await getAuthStatus();
      setStatus(next);
    } catch {
      setStatus({
        auth_required: true,
        authenticated: false,
        user_name: null,
        email: null,
        is_admin: false,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    clearLegacyTokenStorage();
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (loading || !status) return;
    if (status.auth_required && !status.authenticated && pathname !== "/login") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, status, pathname, router]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      await apiLogin(email, password);
      await refresh();
    },
    [refresh],
  );

  const signOut = useCallback(() => {
    void (async () => {
      try {
        await apiLogout();
      } catch {
        clearLegacyTokenStorage();
      }
      setStatus((prev) =>
        prev
          ? { ...prev, authenticated: false, user_name: null, email: null, is_admin: false }
          : prev,
      );
      router.push("/login");
    })();
  }, [router]);

  const value = useMemo(
    () => ({ status, loading, refresh, signIn, signOut }),
    [status, loading, refresh, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth outside AuthProvider");
  return value;
}
