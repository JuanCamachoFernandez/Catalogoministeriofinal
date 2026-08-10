import { AlertTriangle, LoaderCircle } from "lucide-react";
import {
  etiquetaAccionAuditoria,
  accionesAuditoriaNegativas,
  accionesAuditoriaPositivas,
  accionesAuditoriaAdvertencia,
} from "../utilidades/etiquetasAuditoria";

export function EstadoCarga({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="page-state" role="status">
      <LoaderCircle className="animate-spin" />
      {label}
    </div>
  );
}

export function EstadoVacio({
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

export function CajaError({ mensaje }: { mensaje: string }) {
  return (
    <div className="alert-danger flex items-start gap-2" role="alert">
      <AlertTriangle size={20} className="mt-0.5 shrink-0" />
      <span>{mensaje}</span>
    </div>
  );
}

export function ProgresoCarga({ value }: { value: number }) {
  if (value <= 0 || value >= 100) return null;
  return (
    <div
      className="upload-progress"
      role="progressbar"
      aria-label="Carga de imagen"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
    >
      <span style={{ width: `${value}%` }} />
      <small>{value}%</small>
    </div>
  );
}

export function InsigniaEstado({ value }: { value: string | boolean }) {
  const normalized = String(value);
  const positive = [
    "true",
    "ACTIVE",
    "AVAILABLE",
    "AUTHORIZED",
    "PUBLISHED",
    "APPROVED",
  ].includes(normalized) || accionesAuditoriaPositivas.has(normalized);
  const warning = ["PENDING", "DRAFT", "OUT_OF_STOCK"].includes(normalized)
    || accionesAuditoriaAdvertencia.has(normalized);
  const negative = [
    "INACTIVE",
    "LOCKED",
    "BLOCKED",
    "DELETED",
    "LOGICALLY_DELETED",
    "REJECTED",
    "REVOKED",
    "DISABLED",
  ].includes(normalized) || accionesAuditoriaNegativas.has(normalized);
  const labels: Record<string, string> = {
    ACTIVE: "Activo",
    INACTIVE: "Inactivo",
    LOGICALLY_DELETED: "Inhabilitada",
    LOCKED: "Bloqueado",
    AVAILABLE: "Disponible",
    OUT_OF_STOCK: "Agotado",
    DELETED: "Eliminado",
    AUTHORIZED: "Autorizado",
    PENDING: "Pendiente",
    REJECTED: "Rechazado",
    REVOKED: "Retirado",
    PUBLISHED: "Publicada",
    APPROVED: "Aprobada",
    DRAFT: "Preparación",
    RETIRED: "Retirado",
    FINISHED: "Finalizada",
    DISABLED: "Cancelada",
    true: "Activa",
    false: "Inactiva",
  };
  return (
    <span
      className={`status ${
        normalized === "DRAFT"
          ? "status-draft"
          : normalized === "RETIRED"
            ? "status-retired"
          : normalized === "FINISHED"
            ? "status-finished"
          : positive
            ? "status-positive"
            : warning
              ? "status-warning"
              : negative
                ? "status-negative"
                : "status-neutral"
      }`}
    >
      {labels[normalized] ?? etiquetaAccionAuditoria(normalized)}
    </span>
  );
}

