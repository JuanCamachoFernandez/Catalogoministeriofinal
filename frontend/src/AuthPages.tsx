import { Eye, EyeOff, KeyRound, LogIn, Mail, Store } from "lucide-react";
import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api, apiError, type SessionUser } from "./api";
import { useAuth } from "./AuthContext";
import { dashboardFor, isStrongPassword } from "./authUtils";
import { ErrorBox, Field } from "./ui";
import { InstitutionalSeal } from "./Layouts";

function PasswordField({
  label,
  value,
  onChange,
  autoComplete = "current-password",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <Field label={label}>
      <span className="password-input">
        <input
          required
          className="input"
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
        />
        <button
          type="button"
          onClick={() => setVisible(!visible)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
        >
          {visible ? <EyeOff /> : <Eye />}
        </button>
      </span>
    </Field>
  );
}

function AuthShell({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <Link to="/catalogo" className="auth-brand">
          <Store /> Catálogo Digital de Ferias
        </Link>
        <div className="auth-heading">
          <span>{icon}</span>
          <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
        </div>
        {children}
      </section>
      <aside className="auth-aside">
        <InstitutionalSeal className="auth-seal" />
        <div className="auth-aside-copy">
          <strong>
            Una vitrina digital para el talento productivo de Bolivia.
          </strong>
        </div>
      </aside>
    </main>
  );
}

export function LoginPage() {
  const { user, login: saveSession } = useAuth();
  const navigate = useNavigate();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  if (user)
    return (
      <Navigate
        to={
          user.must_change_password
            ? "/gestion/cambiar-contrasena"
            : dashboardFor(user.role)
        }
        replace
      />
    );
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const { data } = await api.post<{
        access_token: string;
        user: SessionUser;
      }>("/auth/login", { login, password });
      saveSession(data.access_token, data.user);
      navigate(
        data.user.must_change_password
          ? "/gestion/cambiar-contrasena"
          : dashboardFor(data.user.role),
        { replace: true },
      );
    } catch (reason) {
      setError(apiError(reason, "No se pudo iniciar sesión."));
    } finally {
      setPending(false);
    }
  };
  return (
    <AuthShell
      title="Bienvenido"
      subtitle="Ingrese sus credenciales para continuar"
      icon={<LogIn />}
    >
      <form onSubmit={submit} className="auth-form">
        <Field label="Usuario">
          <input
            required
            className="input"
            autoComplete="username"
            value={login}
            onChange={(event) => setLogin(event.target.value)}
          />
        </Field>
        <PasswordField
          label="Contraseña"
          value={password}
          onChange={setPassword}
        />
        {error && <ErrorBox message={error} />}
        <button disabled={pending} className="btn w-full">
          {pending ? "Ingresando…" : "Iniciar sesión"}
        </button>
        <Link className="auth-link" to="/gestion/recuperar-contrasena">
          ¿Olvidó su contraseña?
        </Link>
      </form>
    </AuthShell>
  );
}

export function ChangePasswordPage() {
  const { user, refresh, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (next !== confirm)
      return setError("Las contraseñas nuevas no coinciden.");
    if (!isStrongPassword(next))
      return setError(
        "Use al menos 10 caracteres, mayúscula, minúscula, número y símbolo.",
      );
    setPending(true);
    try {
      await api.post("/auth/change-password", {
        current_password: current,
        new_password: next,
      });
      const nextUser = await refresh();
      navigate(nextUser ? dashboardFor(nextUser.role) : "/gestion/login", {
        replace: true,
      });
    } catch (reason) {
      setError(apiError(reason, "No se pudo cambiar la contraseña."));
    } finally {
      setPending(false);
    }
  };
  if (!user) return <Navigate to="/gestion/login" replace />;
  return (
    <AuthShell
      title="Cambie su contraseña"
      subtitle="Proteja su cuenta antes de continuar"
      icon={<KeyRound />}
    >
      <form onSubmit={submit} className="auth-form">
        <PasswordField
          label="Contraseña actual"
          value={current}
          onChange={setCurrent}
        />
        <PasswordField
          label="Nueva contraseña"
          value={next}
          onChange={setNext}
          autoComplete="new-password"
        />
        <PasswordField
          label="Confirmar contraseña"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
        />
        <p className="form-hint">
          Mínimo 10 caracteres con mayúscula, minúscula, número y símbolo.
        </p>
        {error && <ErrorBox message={error} />}
        <button disabled={pending} className="btn w-full">
          Guardar contraseña
        </button>
        <button
          type="button"
          className="auth-link"
          onClick={async () => {
            await logout();
            navigate("/gestion/login");
          }}
        >
          Cerrar sesión
        </button>
      </form>
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  const [step, setStep] = useState<"email" | "code" | "password" | "done">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const requestCode = async () => {
    setPending(true);
    setError("");
    try {
      await api.post("/auth/forgot-password", { email: email.trim().toLowerCase() });
      setCode("");
      setStep("code");
    } catch (reason) {
      setError(apiError(reason, "No se pudo enviar el código."));
    } finally {
      setPending(false);
    }
  };
  const submitEmail = async (event: React.FormEvent) => {
    event.preventDefault();
    await requestCode();
  };
  const verifyCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!/^\d{6}$/.test(code)) return setError("Ingrese los 6 números enviados a su correo.");
    setPending(true);
    try {
      const { data } = await api.post<{ reset_token: string }>("/auth/verify-recovery-code", {
        email: email.trim().toLowerCase(),
        code,
      });
      setResetToken(data.reset_token);
      setStep("password");
    } catch (reason) {
      setError(apiError(reason, "No se pudo verificar el código."));
    } finally {
      setPending(false);
    }
  };
  const resetPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password !== confirm) return setError("Las contraseñas no coinciden.");
    if (!isStrongPassword(password))
      return setError("Use al menos 10 caracteres, mayúscula, minúscula, número y símbolo.");
    setPending(true);
    try {
      await api.post("/auth/reset-password", { token: resetToken, new_password: password });
      setStep("done");
    } catch (reason) {
      setError(apiError(reason, "No se pudo cambiar la contraseña."));
    } finally {
      setPending(false);
    }
  };
  return (
    <AuthShell
      title="Recuperar acceso"
      subtitle="Verifique su correo antes de crear una nueva contraseña"
      icon={<Mail />}
    >
      <div className="recovery-steps" aria-label="Progreso de recuperación">
        <span className={step !== "email" ? "complete" : "active"}>1</span>
        <i />
        <span className={step === "password" || step === "done" ? "complete" : step === "code" ? "active" : ""}>2</span>
        <i />
        <span className={step === "done" ? "complete" : step === "password" ? "active" : ""}>3</span>
      </div>
      {step === "done" ? (
        <div className="success-panel">
          <strong>Contraseña actualizada correctamente</strong>
          <p>Ya puede ingresar a su cuenta utilizando la nueva contraseña.</p>
          <Link to="/gestion/login" className="btn">
            Iniciar sesión
          </Link>
        </div>
      ) : step === "email" ? (
        <form className="auth-form" onSubmit={submitEmail}>
          <Field label="Confirme su correo Gmail">
            <input
              type="email"
              className="input"
              required
              autoComplete="email"
              placeholder="usuario@gmail.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Field>
          <p className="form-hint">Enviaremos un código de 6 números al correo registrado en su cuenta.</p>
          {error && <ErrorBox message={error} />}
          <button className="btn w-full" disabled={pending}>
            {pending ? "Enviando…" : "Enviar código"}
          </button>
          <Link className="auth-link" to="/gestion/login">
            Volver al ingreso
          </Link>
        </form>
      ) : step === "code" ? (
        <form className="auth-form" onSubmit={verifyCode}>
          <div className="recovery-email-notice"><Mail size={18}/><span>Enviamos el código a <strong>{email}</strong></span></div>
          <Field label="Código de verificación">
            <input className="input otp-input" required inputMode="numeric" autoComplete="one-time-code" maxLength={6} placeholder="000000" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}/>
          </Field>
          <p className="form-hint">El código vence en 10 minutos. Después de 5 intentos incorrectos deberá solicitar uno nuevo.</p>
          {error && (
            <ErrorBox message={error}/>
          )}
          <button className="btn w-full" disabled={pending || code.length !== 6}>{pending ? "Verificando…" : "Verificar código"}</button>
          <button type="button" className="auth-link" disabled={pending} onClick={() => void requestCode()}>Reenviar código</button>
          <button type="button" className="auth-link" onClick={() => { setError(""); setStep("email"); }}>Cambiar correo</button>
        </form>
      ) : (
        <form className="auth-form" onSubmit={resetPassword}>
          <div className="recovery-verified"><KeyRound size={20}/><div><strong>Código verificado</strong><small>Ahora puede crear una nueva contraseña.</small></div></div>
          <PasswordField label="Nueva contraseña" value={password} onChange={setPassword} autoComplete="new-password"/>
          <PasswordField label="Confirmar contraseña" value={confirm} onChange={setConfirm} autoComplete="new-password"/>
          <p className="form-hint">Mínimo 10 caracteres con mayúscula, minúscula, número y símbolo.</p>
          {error && (
            <ErrorBox message={error}/>
          )}
          <button className="btn w-full" disabled={pending || !resetToken}>{pending ? "Guardando…" : "Cambiar contraseña"}</button>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState(
    token ? "" : "El enlace no contiene un token válido.",
  );
  const [pending, setPending] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password !== confirm) return setError("Las contraseñas no coinciden.");
    if (!isStrongPassword(password))
      return setError("La contraseña no cumple los requisitos de seguridad.");
    setPending(true);
    try {
      const { data } = await api.post("/auth/reset-password", {
        token,
        new_password: password,
      });
      setMessage(data.message);
    } catch (reason) {
      setError(apiError(reason));
    } finally {
      setPending(false);
    }
  };
  return (
    <AuthShell
      title="Nueva contraseña"
      subtitle="El enlace es válido durante 30 minutos"
      icon={<KeyRound />}
    >
      {message ? (
        <div className="success-panel">
          <strong>{message}</strong>
          <Link to="/gestion/login" className="btn">
            Iniciar sesión
          </Link>
        </div>
      ) : (
        <form className="auth-form" onSubmit={submit}>
          <PasswordField
            label="Nueva contraseña"
            value={password}
            onChange={setPassword}
            autoComplete="new-password"
          />
          <PasswordField
            label="Confirmar contraseña"
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
          />
          {error && <ErrorBox message={error} />}
          <button className="btn w-full" disabled={pending || !token}>
            Restablecer contraseña
          </button>
        </form>
      )}
    </AuthShell>
  );
}
