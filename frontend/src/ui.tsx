import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Info,
  LoaderCircle,
  Search,
  ShieldQuestion,
  Trash2,
  X,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import type { Pagination } from "./api";

const openModalStack: HTMLElement[] = [];

export function Loading({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="page-state" role="status">
      <LoaderCircle className="animate-spin" />
      {label}
    </div>
  );
}

export function Empty({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="alert-danger flex items-start gap-2" role="alert">
      <AlertTriangle size={20} className="mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function UploadProgress({ value }: { value: number }) {
  if (value <= 0 || value >= 100) return null;
  return (
    <div className="upload-progress" role="progressbar" aria-label="Carga de imagen" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}>
      <span style={{ width: `${value}%` }} />
      <small>{value}%</small>
    </div>
  );
}

export function StatusBadge({ value }: { value: string | boolean }) {
  const normalized = String(value);
  const positive = [
    "true",
    "ACTIVE",
    "AVAILABLE",
    "AUTHORIZED",
    "PUBLISHED",
  ].includes(normalized);
  const warning = ["PENDING", "DRAFT", "OUT_OF_STOCK"].includes(normalized);
  const labels: Record<string, string> = {
    ACTIVE: "Activo",
    INACTIVE: "Inactivo",
    LOCKED: "Bloqueado",
    AVAILABLE: "Disponible",
    OUT_OF_STOCK: "Agotado",
    DELETED: "Eliminado",
    AUTHORIZED: "Autorizado",
    PENDING: "Pendiente",
    REJECTED: "Rechazado",
    REVOKED: "Revocado",
    PUBLISHED: "Publicada",
    DRAFT: "En preparación",
    FINISHED: "Finalizada",
    DISABLED: "Cancelada",
    true: "Activa",
    false: "Inactiva",
  };
  return (
    <span
      className={`status ${positive ? "status-positive" : warning ? "status-warning" : "status-negative"}`}
    >
      {labels[normalized] ?? normalized}
    </span>
  );
}

export function PaginationBar({
  pagination,
  onPage,
  onPageChange,
}: {
  pagination: Pagination;
  onPage?: (page: number) => void;
  onPageChange?: (page: number) => void;
}) {
  const changePage = onPage ?? onPageChange ?? (() => undefined);
  if (!pagination.total) return null;
  return (
    <div className="pagination" aria-label="Paginación">
      <span>
        Página {pagination.page} de {Math.max(1, pagination.pages)} ·{" "}
        {pagination.total} registros
      </span>
      <div className="flex gap-2">
        <button
          className="btn-outline"
          disabled={!pagination.has_prev}
          onClick={() => changePage(pagination.page - 1)}
          aria-label="Página anterior"
        >
          <ChevronLeft size={18} />
        </button>
        <button
          className="btn-outline"
          disabled={!pagination.has_next}
          onClick={() => changePage(pagination.page + 1)}
          aria-label="Página siguiente"
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

export function SearchField({
  value,
  onChange,
  placeholder = "Buscar…",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="search-field">
      <Search size={18} />
      <span className="sr-only">Buscar</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Limpiar búsqueda"
        >
          <X size={17} />
        </button>
      )}
    </label>
  );
}

export type SearchableOption = { value: string; label: string };

export function SearchableSelect({
  value,
  options,
  onChange,
  placeholder = "Seleccione…",
  searchPlaceholder = "Buscar…",
  disabled = false,
  allowCustom = false,
  onDelete,
  ariaLabel,
}: {
  value: string;
  options: SearchableOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  allowCustom?: boolean;
  onDelete?: (option: SearchableOption) => void | Promise<void>;
  ariaLabel?: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = options.find((option) => option.value === value);
  const normalized = query.trim().toLocaleLowerCase("es");
  const filtered = options.filter((option) =>
    option.label.toLocaleLowerCase("es").includes(normalized),
  );
  const customValue = query.trim();
  const customExists = options.some(
    (option) =>
      option.label.toLocaleLowerCase("es") ===
      customValue.toLocaleLowerCase("es"),
  );

  useEffect(() => {
    const closeOutside = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  const toggle = () => {
    if (disabled) return;
    setOpen((current) => {
      if (!current) {
        setQuery("");
        setTimeout(() => search.current?.focus(), 0);
      }
      return !current;
    });
  };
  const choose = (nextValue: string) => {
    onChange(nextValue);
    setOpen(false);
    setQuery("");
  };

  return (
    <div className={`searchable-select ${open ? "is-open" : ""}`} ref={root}>
      <button
        type="button"
        className="searchable-select-trigger"
        disabled={disabled}
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={toggle}
      >
        <span className={selected || value ? "" : "placeholder"}>
          {(selected?.label ?? value) || placeholder}
        </span>
        <ChevronDown size={18} />
      </button>
      {open && (
        <div className="searchable-select-menu">
          <label className="searchable-select-search">
            <Search size={17} />
            <input
              ref={search}
              value={query}
              placeholder={searchPlaceholder}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") setOpen(false);
                if (
                  event.key === "Enter" &&
                  allowCustom &&
                  customValue &&
                  !customExists
                ) {
                  event.preventDefault();
                  choose(customValue);
                }
              }}
            />
          </label>
          <div className="searchable-select-options" role="listbox">
            {filtered.map((option) => (
              <div
                className={`searchable-select-option ${option.value === value ? "selected" : ""}`}
                key={option.value}
              >
                <button type="button" onClick={() => choose(option.value)}>
                  {option.label}
                </button>
                {onDelete && option.value && (
                  <button
                    type="button"
                    className="searchable-select-delete"
                    aria-label={`Eliminar ${option.label}`}
                    onClick={() => onDelete(option)}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            ))}
            {allowCustom && customValue && !customExists && (
              <button
                type="button"
                className="searchable-select-custom"
                onClick={() => choose(customValue)}
              >
                Usar nueva opción: <strong>{customValue}</strong>
              </button>
            )}
            {!filtered.length && !(allowCustom && customValue) && (
              <p className="searchable-select-empty">Sin coincidencias</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const dialog = useRef<HTMLElement>(null);
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialogElement = dialog.current;
    dialogElement?.focus();
    if (dialogElement) openModalStack.push(dialogElement);
    document.body.classList.add("modal-open");
    const handleKeyboard = (event: KeyboardEvent) => {
      if (openModalStack.at(-1) !== dialogElement) return;
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogElement) return;
      const focusable = [...dialogElement.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )].filter((element) => !element.hasAttribute("hidden"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyboard);
    return () => {
      document.removeEventListener("keydown", handleKeyboard);
      const index = dialogElement ? openModalStack.lastIndexOf(dialogElement) : -1;
      if (index >= 0) openModalStack.splice(index, 1);
      if (!openModalStack.length) document.body.classList.remove("modal-open");
      previous?.focus();
    };
  }, [onClose]);
  return createPortal(
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        ref={dialog}
        tabIndex={-1}
        className={`modal ${wide ? "modal-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="modal-header">
          <h2 id={titleId}>{title}</h2>
          <button onClick={onClose} aria-label="Cerrar">
            <X />
          </button>
        </header>
        {children}
      </section>
    </div>,
    document.body,
  );
}

type FeedbackTone = "success" | "error" | "info" | "warning";

type FeedbackNotice = {
  kind: "notice";
  title: string;
  message?: string;
  tone: FeedbackTone;
  autoClose: boolean;
};

type FeedbackConfirmation = {
  kind: "confirm";
  title: string;
  message: string;
  confirmLabel: string;
  danger: boolean;
  resolve: (confirmed: boolean) => void;
};

type FeedbackState = FeedbackNotice | FeedbackConfirmation;

type FeedbackContextValue = {
  notify: (options: {
    title: string;
    message?: string;
    tone?: FeedbackTone;
    autoClose?: boolean;
  }) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  confirm: (options: {
    title?: string;
    message: string;
    confirmLabel?: string;
    danger?: boolean;
  }) => Promise<boolean>;
};

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

const feedbackIcons = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

export function FeedbackProvider({ children }: { children: React.ReactNode }) {
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const close = useCallback((confirmed = false) => {
    setFeedback((current) => {
      if (current?.kind === "confirm") current.resolve(confirmed);
      return null;
    });
  }, []);

  const notify = useCallback<FeedbackContextValue["notify"]>((options) => {
    setFeedback((current) => {
      if (current?.kind === "confirm") current.resolve(false);
      return {
        kind: "notice",
        title: options.title,
        message: options.message,
        tone: options.tone ?? "info",
        autoClose: options.autoClose ?? true,
      };
    });
  }, []);

  const confirm = useCallback<FeedbackContextValue["confirm"]>((options) => {
    return new Promise<boolean>((resolve) => {
      setFeedback((current) => {
        if (current?.kind === "confirm") current.resolve(false);
        return {
          kind: "confirm",
          title: options.title ?? "Confirmar acción",
          message: options.message,
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

  const value = useMemo<FeedbackContextValue>(
    () => ({
      notify,
      success: (title, message) => notify({ title, message, tone: "success" }),
      error: (title, message) => notify({ title, message, tone: "error" }),
      confirm,
    }),
    [confirm, notify],
  );

  const tone = feedback?.kind === "notice" ? feedback.tone : "warning";
  const Icon = feedback?.kind === "confirm" ? ShieldQuestion : feedbackIcons[tone];

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      {feedback && (
        <Modal title={feedback.title} onClose={() => close(false)}>
          <div className={`feedback-dialog feedback-${tone}`}>
            <div className="feedback-icon" aria-hidden="true">
              <Icon />
            </div>
            {feedback.message && <p>{feedback.message}</p>}
            <div className="modal-actions feedback-actions">
              {feedback.kind === "confirm" && (
                <button
                  type="button"
                  className="btn-outline"
                  onClick={() => close(false)}
                >
                  Cancelar
                </button>
              )}
              <button
                type="button"
                className={
                  feedback.kind === "confirm" && feedback.danger
                    ? "btn-danger"
                    : "btn"
                }
                onClick={() => close(true)}
                autoFocus
              >
                {feedback.kind === "confirm" ? feedback.confirmLabel : "OK"}
              </button>
            </div>
            {feedback.kind === "notice" && feedback.autoClose && (
              <div className="feedback-timeout" aria-hidden="true" />
            )}
          </div>
        </Modal>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (!context)
    throw new Error("useFeedback debe utilizarse dentro de FeedbackProvider");
  return context;
}

export function ConfirmButton({
  children,
  question,
  onConfirm,
  className = "btn-danger",
  disabled = false,
}: {
  children: React.ReactNode;
  question: string;
  onConfirm: () => void;
  className?: string;
  disabled?: boolean;
}) {
  const feedback = useFeedback();
  return (
    <button
      type="button"
      disabled={disabled}
      className={className}
      onClick={async () => {
        const confirmed = await feedback.confirm({
          title: "Confirmar acción",
          message: question,
          confirmLabel: "Sí, continuar",
          danger: className.includes("danger"),
        });
        if (confirmed) onConfirm();
      }}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
