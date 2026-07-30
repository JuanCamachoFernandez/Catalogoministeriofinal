import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Info,
  ShieldQuestion,
  X,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { Modal } from "./Modal";

type RetroalimentacionTone = "success" | "error" | "info" | "warning";

type RetroalimentacionNotice = {
  kind: "notice";
  title: string;
  mensaje?: string;
  tone: RetroalimentacionTone;
  autoClose: boolean;
  onClose?: () => void;
};

type RetroalimentacionConfirmation = {
  kind: "confirm";
  title: string;
  mensaje: string;
  confirmLabel: string;
  danger: boolean;
  resolve: (confirmed: boolean) => void;
};

type RetroalimentacionState = RetroalimentacionNotice | RetroalimentacionConfirmation;

type RetroalimentacionContextValue = {
  notify: (options: {
    title: string;
    mensaje?: string;
    tone?: RetroalimentacionTone;
    autoClose?: boolean;
    onClose?: () => void;
  }) => void;
  success: (title: string, mensaje?: string) => void;
  error: (title: string, mensaje?: string) => void;
  confirm: (options: {
    title?: string;
    mensaje: string;
    confirmLabel?: string;
    danger?: boolean;
  }) => Promise<boolean>;
};

const RetroalimentacionContext = createContext<RetroalimentacionContextValue | null>(null);

const feedbackIcons = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

export function ProveedorRetroalimentacion({ children }: { children: React.ReactNode }) {
  const [feedback, setRetroalimentacion] = useState<RetroalimentacionState | null>(null);

  const close = useCallback((confirmed = false) => {
    setRetroalimentacion((current) => {
      if (current?.kind === "confirm") current.resolve(confirmed);
      if (current?.kind === "notice" && current.onClose) {
        window.setTimeout(current.onClose, 0);
      }
      return null;
    });
  }, []);

  const notify = useCallback<RetroalimentacionContextValue["notify"]>((options) => {
    setRetroalimentacion((current) => {
      if (current?.kind === "confirm") current.resolve(false);
      return {
        kind: "notice",
        title: options.title,
        mensaje: options.mensaje,
        tone: options.tone ?? "info",
        autoClose: options.autoClose ?? true,
        onClose: options.onClose,
      };
    });
  }, []);

  const confirm = useCallback<RetroalimentacionContextValue["confirm"]>((options) => {
    return new Promise<boolean>((resolve) => {
      setRetroalimentacion((current) => {
        if (current?.kind === "confirm") current.resolve(false);
        return {
          kind: "confirm",
          title: options.title ?? "Confirmar acción",
          mensaje: options.mensaje,
          confirmLabel: options.confirmLabel ?? "Confirmar",
          danger: options.danger ?? false,
          resolve,
        };
      });
    });
  }, []);

  useEffect(() => {
    if (feedback?.kind !== "notice" || !feedback.autoClose) return;
    const timer = window.setTimeout(() => close(), 5000);
    return () => window.clearTimeout(timer);
  }, [close, feedback]);

  const value = useMemo<RetroalimentacionContextValue>(
    () => ({
      notify,
      success: (title, mensaje) => notify({ title, mensaje, tone: "success" }),
      error: (title, mensaje) => notify({ title, mensaje, tone: "error" }),
      confirm,
    }),
    [confirm, notify],
  );

  const tone = feedback?.kind === "notice" ? feedback.tone : "warning";
  const Icon =
    feedback?.kind === "confirm" ? ShieldQuestion : feedbackIcons[tone];

  return (
    <RetroalimentacionContext.Provider value={value}>
      {children}
      {feedback?.kind === "notice" &&
        createPortal(
          <aside
            className={`feedback-toast feedback-${tone}`}
            role={tone === "error" || tone === "warning" ? "alert" : "status"}
            aria-live={
              tone === "error" || tone === "warning" ? "assertive" : "polite"
            }
          >
            <div className="feedback-toast-icon" aria-hidden="true">
              <Icon />
            </div>
            <div className="feedback-toast-copy">
              <strong>{feedback.title}</strong>
              {feedback.mensaje && <p>{feedback.mensaje}</p>}
            </div>
            <button
              type="button"
              className="feedback-toast-close"
              onClick={() => close(false)}
              aria-label="Cerrar notificación"
            >
              <X />
            </button>
            {feedback.autoClose && (
              <div className="feedback-timeout" aria-hidden="true" />
            )}
          </aside>,
          document.body,
        )}
      {feedback?.kind === "confirm" && (
        <Modal title={feedback.title} onClose={() => close(false)} className="confirm-modal">
          <div className={`feedback-dialog feedback-${tone}`}>
            <div className="feedback-icon" aria-hidden="true">
              <Icon />
            </div>
            <p>{feedback.mensaje}</p>
            <div className="modal-actions feedback-actions">
              <button
                type="button"
                className="btn-outline"
                onClick={() => close(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className={feedback.danger ? "btn-danger" : "btn"}
                onClick={() => close(true)}
                autoFocus
              >
                {feedback.confirmLabel}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </RetroalimentacionContext.Provider>
  );
}

export function useRetroalimentacion() {
  const context = useContext(RetroalimentacionContext);
  if (!context)
    throw new Error("useRetroalimentacion debe utilizarse dentro de ProveedorRetroalimentacion");
  return context;
}


