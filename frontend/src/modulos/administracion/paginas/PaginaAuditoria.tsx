import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Eye, History, UserRound } from "lucide-react";
import { useState } from "react";
import { errorApi, paginacionVacia } from "../../../compartido";
import {
  BarraPaginacion,
  CajaError,
  Campo,
  CampoBusqueda,
  EstadoCarga,
  EstadoVacio,
  Modal,
  SelectorBuscable,
  useElementosPaginacionAdaptable,
} from "../../../compartido/componentes";
import {
  etiquetaAccionAuditoria,
  etiquetaDescripcionAuditoria,
  etiquetaEntidadAuditoria,
} from "../../../compartido/utilidades/etiquetasAuditoria";
import { servicioAuditoria } from "../servicios/servicioAuditoria";

type AuditDetail = {
  id: string;
  usuario: string;
  accion: string;
  entidad: string;
  entidad_id?: string | null;
  valores_anteriores?: unknown;
  valores_nuevos?: unknown;
  direccion_ip?: string | null;
  fecha_hora: string;
  resultado?: string | null;
  detalle?: string | null;
};

const AUDIT_ACTION_OPTIONS = [{ value: "", label: "Todas las acciones" }];

const dateParts = (value: string) => {
  const date = new Date(value);
  return {
    date: new Intl.DateTimeFormat("es-BO", { dateStyle: "medium" }).format(date),
    time: new Intl.DateTimeFormat("es-BO", { timeStyle: "medium" }).format(date),
  };
};

const formatAuditValue = (value: unknown): string => {
  if (value === null || value === undefined || value === "") {
    return "Sin registro";
  }
  if (typeof value === "boolean") {
    return value ? "Sí" : "No";
  }
  if (Array.isArray(value)) {
    return value.length
      ? value.map((item) => formatAuditValue(item)).join(", ")
      : "Sin registro";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
};

const formatAuditLabel = (path: string): string =>
  path
    .split(".")
    .filter(Boolean)
    .map((segment) =>
      segment
        .replaceAll("_", " ")
        .replace(/\[(\d+)\]/g, " $1")
        .replace(/^\w/, (letter) => letter.toUpperCase()),
    )
    .join(" / ");

const auditEntries = (
  value: unknown,
  parentKey = "",
): Array<{ label: string; value: string }> => {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) {
    if (!value.length) return [];
    if (value.every((item) => typeof item !== "object" || item === null)) {
      return [{ label: formatAuditLabel(parentKey), value: formatAuditValue(value) }];
    }
    return value.flatMap((item, index) =>
      auditEntries(item, parentKey ? `${parentKey}[${index + 1}]` : `[${index + 1}]`),
    );
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).flatMap(
      ([key, nestedValue]) =>
        auditEntries(nestedValue, parentKey ? `${parentKey}.${key}` : key),
    );
    return entries.length
      ? entries
      : [{ label: formatAuditLabel(parentKey), value: formatAuditValue(value) }];
  }
  return [{ label: formatAuditLabel(parentKey), value: formatAuditValue(value) }];
};

export function PaginaAuditoria() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const audits = useQuery({
    queryKey: ["admin-audits", q, action, dateFrom, dateTo, page],
    queryFn: () =>
      servicioAuditoria.list({
        q: q || undefined,
        action: action || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        per_page: 20,
      }),
  });
  const detail = useQuery({
    queryKey: ["admin-audit", selectedId],
    enabled: Boolean(selectedId),
    queryFn: () => servicioAuditoria.detail<AuditDetail>(selectedId!),
  });

  const data = audits.data ?? { items: [], pagination: paginacionVacia };
  const displayedAudits = useElementosPaginacionAdaptable(
    data.items,
    data.pagination,
    `${q}|${action}|${dateFrom}|${dateTo}`,
  );
  const actionOptions = [
    ...AUDIT_ACTION_OPTIONS,
    ...[...new Set(displayedAudits.map((item) => item.accion))]
      .sort()
      .map((item) => ({
        value: item,
        label: etiquetaAccionAuditoria(item),
      })),
  ];
  const previousEntries = detail.data
    ? auditEntries(detail.data.valores_anteriores)
    : [];
  const nextEntries = detail.data ? auditEntries(detail.data.valores_nuevos) : [];

  const resetPage = () => setPage(1);

  return (
    <section className="admin-page admin-requests-page admin-audit-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Seguridad y trazabilidad</span>
          <h1>Auditoría del sistema</h1>
          <p>
            Registro de usuarios, fecha, hora, acción y descripción de cada
            operación.
          </p>
        </div>
        <span className="heading-icon">
          <History />
        </span>
      </header>

      <div className="toolbar admin-requests-toolbar">
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            resetPage();
          }}
          placeholder="Buscar usuario, acción o descripción..."
        />
        <SelectorBuscable
          value={action}
          options={actionOptions}
          onChange={(value) => {
            setAction(value);
            resetPage();
          }}
          placeholder="Todas las acciones"
          searchPlaceholder="Buscar acción..."
          ariaLabel="Filtrar por acción"
        />
        <Campo label="Desde">
          <input
            className="input"
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(event) => {
              setDateFrom(event.target.value);
              resetPage();
            }}
          />
        </Campo>
        <Campo label="Hasta">
          <input
            className="input"
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(event) => {
              setDateTo(event.target.value);
              resetPage();
            }}
          />
        </Campo>
      </div>

      {audits.isLoading && !displayedAudits.length ? (
        <EstadoCarga label="Cargando auditoría..." />
      ) : audits.error ? (
        <CajaError
          mensaje={errorApi(audits.error, "No se pudo cargar la auditoría.")}
        />
      ) : displayedAudits.length ? (
        <>
          <div className="table-wrap audit-list-table">
            <table>
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Fecha</th>
                  <th>Hora</th>
                  <th>Acción</th>
                  <th>Descripción</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {displayedAudits.map((item) => {
                  const parts = dateParts(item.created_at);
                  return (
                    <tr key={item.id}>
                      <td>
                        <span className="table-user">
                          <UserRound size={17} />
                          <strong>{item.usuario}</strong>
                        </span>
                      </td>
                      <td>{parts.date}</td>
                      <td className="table-time">{parts.time}</td>
                      <td>
                        <span className="action-pill">
                          {etiquetaAccionAuditoria(item.accion)}
                        </span>
                        <small>{etiquetaEntidadAuditoria(item.entidad)}</small>
                      </td>
                      <td className="audit-description">
                        {etiquetaDescripcionAuditoria(item.descripcion)}
                      </td>
                      <td>
                        <button
                          className="btn-icon"
                          onClick={() => setSelectedId(item.id)}
                          aria-label={`Ver detalle de ${etiquetaAccionAuditoria(item.accion)}`}
                        >
                          <Eye size={18} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <BarraPaginacion
            pagination={data.pagination}
            onPageChange={setPage}
            mobileLabel="Ver más registros"
          />
        </>
      ) : (
        <EstadoVacio
          title="No hay registros para estos filtros"
          description="Pruebe con otro período o limpie la búsqueda."
        />
      )}

      {selectedId && (
        <Modal
          title="Detalle de auditoría"
          onClose={() => setSelectedId(null)}
          className="admin-sector-modal admin-audit-modal"
        >
          {detail.isLoading ? (
            <EstadoCarga />
          ) : detail.error || !detail.data ? (
            <CajaError mensaje={errorApi(detail.error)} />
          ) : (
            <div className="audit-detail">
              <div className="audit-detail-summary">
                <CalendarClock />
                <div>
                  <p>{detail.data.usuario}</p>
                  <span>
                    {dateParts(detail.data.fecha_hora).date} ·{" "}
                    {dateParts(detail.data.fecha_hora).time}
                  </span>
                </div>
              </div>
              <dl>
                <div>
                  <dt>Qué pasó</dt>
                  <dd>{etiquetaAccionAuditoria(detail.data.accion)}</dd>
                </div>
                <div>
                  <dt>Sección del sistema</dt>
                  <dd>{etiquetaEntidadAuditoria(detail.data.entidad)}</dd>
                </div>
                <div>
                  <dt>Detalle</dt>
                  <dd>{etiquetaDescripcionAuditoria(detail.data.detalle)}</dd>
                </div>
              </dl>
              {Boolean(
                detail.data.valores_anteriores || detail.data.valores_nuevos,
              ) && (
                <div className="audit-changes">
                  <article>
                    <h3>Antes</h3>
                    {previousEntries.length ? (
                      <div className="audit-change-list">
                        {previousEntries.map((entry) => (
                          <div
                            className="audit-change-item"
                            key={`before-${entry.label}-${entry.value}`}
                          >
                            <span>{entry.label}</span>
                            <p>{entry.value}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="audit-change-empty">Sin cambios registrados.</p>
                    )}
                  </article>
                  <article>
                    <h3>Después</h3>
                    {nextEntries.length ? (
                      <div className="audit-change-list">
                        {nextEntries.map((entry) => (
                          <div
                            className="audit-change-item"
                            key={`after-${entry.label}-${entry.value}`}
                          >
                            <span>{entry.label}</span>
                            <p>{entry.value}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="audit-change-empty">Sin cambios registrados.</p>
                    )}
                  </article>
                </div>
              )}
            </div>
          )}
        </Modal>
      )}
    </section>
  );
}
