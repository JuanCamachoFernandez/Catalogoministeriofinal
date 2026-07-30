import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import type { SessionUser } from "../../../compartido";
import { inicioParaRol, tieneRol, type UserRole } from "../../../compartido/autenticacion/roles";
import { servicioAutenticacion } from "../servicios/servicioAutenticacion";

type AuthValue = {
  user: SessionUser | null;
  loading: boolean;
  login: (accessToken: string, user: SessionUser, refreshToken?: string) => void;
  logout: () => Promise<void>;
  refresh: () => Promise<SessionUser | null>;
};

const ContextoAutenticacion = createContext<AuthValue | null>(null);
const TOKEN_KEY = "catalog_token";
const REFRESH_KEY = "catalog_refresh_token";
const USER_KEY = "catalog_user";

function storedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) ?? "null") as SessionUser | null;
  } catch {
    return null;
  }
}

export function ProveedorAutenticacion({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<SessionUser | null>(storedUser);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));

  const clear = useCallback(() => {
    const currentUser = storedUser();
    if (currentUser?.id) localStorage.removeItem(`catalog_last_activity:${currentUser.id}`);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    queryClient.clear();
    setUser(null);
  }, [queryClient]);

  const login = useCallback((accessToken: string, nextUser: SessionUser, refreshToken?: string) => {
    queryClient.clear();
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
    else localStorage.removeItem(REFRESH_KEY);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    localStorage.setItem(`catalog_last_activity:${nextUser.id}`, String(Date.now()));
    setUser(nextUser);
  }, [queryClient]);

  const refresh = useCallback(async () => {
    if (!localStorage.getItem(TOKEN_KEY)) {
      clear();
      setLoading(false);
      return null;
    }
    try {
      const previousUserId = storedUser()?.id;
      const data = await servicioAutenticacion.me();
      if (previousUserId && previousUserId !== data.id) queryClient.clear();
      localStorage.setItem(USER_KEY, JSON.stringify(data));
      setUser(data);
      return data;
    } catch {
      clear();
      return null;
    } finally {
      setLoading(false);
    }
  }, [clear, queryClient]);

  const logout = useCallback(async () => {
    const sessionToken = localStorage.getItem(TOKEN_KEY) ?? localStorage.getItem(REFRESH_KEY);
    try {
      if (sessionToken) {
        await servicioAutenticacion.logout(sessionToken);
      }
    } finally {
      clear();
    }
  }, [clear]);

  useEffect(() => {
    // La sesión se sincroniza una sola vez con la fuente externa (el backend).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const unauthorized = () => clear();
    window.addEventListener("catalog:unauthorized", unauthorized);
    return () => window.removeEventListener("catalog:unauthorized", unauthorized);
  }, [clear]);

  useEffect(() => {
    const syncLogout = (event: StorageEvent) => {
      if (
        (event.key === TOKEN_KEY || event.key === REFRESH_KEY || event.key === USER_KEY)
        && event.newValue === null
      ) {
        clear();
        setLoading(false);
      }
    };
    window.addEventListener("storage", syncLogout);
    return () => window.removeEventListener("storage", syncLogout);
  }, [clear]);

  const value = useMemo(() => ({ user, loading, login, logout, refresh }), [user, loading, login, logout, refresh]);
  return <ContextoAutenticacion.Provider value={value}>{children}</ContextoAutenticacion.Provider>;
}

export function useAutenticacion() {
  const value = useContext(ContextoAutenticacion);
  if (!value) throw new Error("useAutenticacion debe utilizarse dentro de ProveedorAutenticacion");
  return value;
}

export function RutaProtegida({ roles, children }: { roles?: readonly UserRole[]; children: React.ReactNode }) {
  const { user, loading } = useAutenticacion();
  const location = useLocation();
  if (loading) return <main className="page-state">Verificando sesión…</main>;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (user.must_change_password && location.pathname !== "/cambiar-password") {
    return <Navigate to="/cambiar-password" replace />;
  }
  if (roles && !tieneRol(user.role, roles)) return <Navigate to={inicioParaRol(user.role)} replace />;
  return <>{children}</>;
}
