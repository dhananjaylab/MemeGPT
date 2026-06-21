import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { User } from '../lib/types';
import { apiClient, setAccessToken } from '../lib/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Phase 1 security remediation: the access token is never persisted to
  // localStorage anymore (that was a direct XSS-token-theft exposure).
  // Session continuity instead comes from the httpOnly refresh cookie the
  // backend sets on login — on every app boot we silently try to exchange
  // it for a fresh access token. If there's no valid cookie (new browser,
  // logged out, cookie expired), this simply 401s and we fall back to
  // "logged out" — no different from the old "no token in localStorage" case.
  useEffect(() => {
    let cancelled = false;

    apiClient
      .refreshAccessToken()
      .then((res) => {
        if (cancelled) return;
        setAccessToken(res.access_token);
        setToken(res.access_token);
        setUser(res.user);
      })
      .catch(() => {
        if (cancelled) return;
        setAccessToken(null);
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const login = (newToken: string, userData: User) => {
    // The refresh-token cookie was already set by the backend as part of
    // whatever call produced newToken (POST /api/auth/login or the OAuth
    // callback redirect) — we only ever hold the short-lived access token
    // here, and only in memory.
    setAccessToken(newToken);
    setToken(newToken);
    setUser(userData);
  };

  const logout = () => {
    apiClient.logout().catch(() => {
      // Best-effort — even if the network call fails, clear local state
      // and the cookie will simply expire on its own.
    });
    setAccessToken(null);
    setToken(null);
    setUser(null);
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      token, 
      isAuthenticated: !!token, 
      isLoading,
      login,
      logout 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
