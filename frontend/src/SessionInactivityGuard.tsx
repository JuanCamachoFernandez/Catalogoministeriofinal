import { Clock3, Eye, EyeOff, LockKeyhole, LogOut } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiError } from "./api";
import { useAuth } from "./AuthContext";

export const LOCK_AFTER_MS = 2 * 60 * 1000;
export const LOGOUT_AFTER_MS = 5 * 60 * 1000;

export function inactivityStatus(elapsed: number) {
  if (elapsed >= LOGOUT_AFTER_MS) return "expired" as const;
  if (elapsed >= LOCK_AFTER_MS) return "locked" as const;
  return "active" as const;
}

export function SessionInactivityGuard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [locked, setLocked] = useState(false);
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const lockedRef = useRef(false);
  const closingRef = useRef(false);
  const lastActivityRef = useRef(0);
  const lastRecordedRef = useRef(0);
  const activityKey = `catalog_last_activity:${user?.id ?? "anonymous"}`;

  useEffect(() => {
    lockedRef.current = locked;
  }, [locked]);

  const recordActivity = useCallback(() => {
    if (lockedRef.current || closingRef.current) return;
    const now = Date.now();
    if (now - lastRecordedRef.current < 1000) return;
    lastRecordedRef.current = now;
    lastActivityRef.current = now;
    localStorage.setItem(activityKey, String(now));
  }, [activityKey]);

  const closeForInactivity = useCallback(async () => {
    if (closingRef.current) return;
    closingRef.current = true;
    await logout();
    navigate("/login?motivo=inactividad", { replace: true });
  }, [logout, navigate]);

  useEffect(() => {
    const stored = Number(localStorage.getItem(activityKey));
    const initial = Number.isFinite(stored) && stored > 0 ? stored : Date.now();
    lastActivityRef.current = initial;
    if (!stored) localStorage.setItem(activityKey, String(initial));

    const check = () => {
      const status = inactivityStatus(Date.now() - lastActivityRef.current);
      if (status === "expired") void closeForInactivity();
      else if (status === "locked") setLocked(true);
    };
    const events: Array<keyof WindowEventMap> = ["pointerdown", "keydown", "mousemove", "scroll", "touchstart"];
    events.forEach((name) => window.addEventListener(name, recordActivity, { passive: true }));
    const storage = (event: StorageEvent) => {
      if (event.key !== activityKey || !event.newValue) return;
      const value = Number(event.newValue);
      if (!Number.isFinite(value)) return;
      lastActivityRef.current = value;
      if (inactivityStatus(Date.now() - value) === "active") {
        setLocked(false);
        setError("");
        setPassword("");
      }
    };
    window.addEventListener("storage", storage);
    const interval = window.setInterval(check, 1000);
    check();
    return () => {
      events.forEach((name) => window.removeEventListener(name, recordActivity));
      window.removeEventListener("storage", storage);
      window.clearInterval(interval);
    };
  }, [activityKey, closeForInactivity, recordActivity]);

  const unlock = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!password) return setError("Ingrese su contraseña para continuar.");
    setPending(true);
    setError("");
    try {
      await api.post("/auth/reauthenticate", { current_password: password });
      const now = Date.now();
      lastActivityRef.current = now;
      localStorage.setItem(activityKey, String(now));
      setPassword("");
      setVisible(false);
      setLocked(false);
    } catch (reason) {
      setError(apiError(reason, "No se pudo desbloquear la sesión."));
    } finally {
      setPending(false);
    }
  };

  if (!locked) return null;
  return <div className="session-lock-backdrop" role="dialog" aria-modal="true" aria-labelledby="session-lock-title">
    <section className="session-lock-card">
      <header className="session-lock-heading">
        <span className="session-lock-icon" aria-hidden="true"><LockKeyhole/></span>
        <div>
          <small>Sesión bloqueada</small>
          <h2 id="session-lock-title">Confirme su contraseña</h2>
        </div>
      </header>
      <p>La sesión de <strong>{user?.username}</strong> se pausó después de 2 minutos sin actividad.</p>
      <form onSubmit={unlock}>
        <label>Contraseña actual</label>
        <span className="password-input">
          <input className="input" autoFocus type={visible ? "text" : "password"} value={password} autoComplete="current-password" onChange={(event) => setPassword(event.target.value)}/>
          <button type="button" onClick={() => setVisible((current) => !current)} aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}>{visible ? <EyeOff/> : <Eye/>}</button>
        </span>
        {error && <div className="alert-danger">{error}</div>}
        <button className="btn w-full" disabled={pending}>{pending ? "Verificando…" : "Continuar"}</button>
      </form>
      <button className="session-lock-logout" onClick={() => void closeForInactivity()}><LogOut size={18}/>Cerrar sesión</button>
      <small className="session-lock-timeout"><Clock3/>La sesión se cerrará al cumplir 5 minutos de inactividad.</small>
    </section>
  </div>;
}
