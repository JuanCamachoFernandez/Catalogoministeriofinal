import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Eye, History, UserRound } from "lucide-react";
import { useState } from "react";
import { api, apiError, emptyPagination, type AuditItem, type Paged } from "./api";
import { Empty, ErrorBox, Field, Loading, Modal, PaginationBar, SearchField } from "./ui";

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

const dateParts = (value: string) => {
  const date = new Date(value);
  return {
    date: new Intl.DateTimeFormat("es-BO", { dateStyle: "medium" }).format(date),
    time: new Intl.DateTimeFormat("es-BO", { timeStyle: "medium" }).format(date),
  };
};

const actionLabel = (value: string) => value.replaceAll("_", " ");

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const audits = useQuery({
    queryKey: ["admin-audits", q, action, dateFrom, dateTo, page],
    queryFn: () => api.get<Paged<AuditItem>>("/admin/audits", {
      params: { q: q || undefined, action: action || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, page, per_page: 20 },
    }).then((response) => response.data),
  });
  const detail = useQuery({
    queryKey: ["admin-audit", selectedId],
    enabled: Boolean(selectedId),
    queryFn: () => api.get<AuditDetail>(`/admin/audits/${selectedId}`).then((response) => response.data),
  });

  const data = audits.data ?? { items: [], pagination: emptyPagination };
  const actions = [...new Set(data.items.map((item) => item.accion))].sort();
  const resetPage = () => setPage(1);

  return (
    <section>
      <header className="page-heading">
        <div><span className="eyebrow">Seguridad y trazabilidad</span><h1>Auditoría del sistema</h1><p>Registro de usuarios, fecha, hora, acción y descripción de cada operación.</p></div>
        <span className="heading-icon"><History /></span>
      </header>

      <div className="panel filter-panel">
        <SearchField value={q} onChange={(value) => { setQ(value); resetPage(); }} placeholder="Buscar usuario, acción o descripción…" />
        <Field label="Acción"><select className="input" value={action} onChange={(event) => { setAction(event.target.value); resetPage(); }}><option value="">Todas las acciones</option>{actions.map((item) => <option key={item} value={item}>{actionLabel(item)}</option>)}</select></Field>
        <Field label="Desde"><input className="input" type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); resetPage(); }} /></Field>
        <Field label="Hasta"><input className="input" type="date" value={dateTo} onChange={(event) => { setDateTo(event.target.value); resetPage(); }} /></Field>
      </div>

      {audits.isLoading ? <Loading label="Cargando auditoría…" /> : audits.error ? <ErrorBox message={apiError(audits.error, "No se pudo cargar la auditoría.")} /> : data.items.length ? (
        <>
          <div className="table-wrap audit-list-table">
            <table>
              <thead><tr><th>Usuario</th><th>Fecha</th><th>Hora</th><th>Acción</th><th>Descripción</th><th aria-label="Acciones" /></tr></thead>
              <tbody>{data.items.map((item) => { const parts = dateParts(item.created_at); return (
                <tr key={item.id}>
                  <td><span className="table-user"><UserRound size={17} /><strong>{item.usuario}</strong></span></td>
                  <td>{parts.date}</td><td className="table-time">{parts.time}</td>
                  <td><span className="action-pill">{actionLabel(item.accion)}</span><small>{item.entidad}</small></td>
                  <td className="audit-description">{item.descripcion || "Operación registrada"}</td>
                  <td><button className="btn-icon" onClick={() => setSelectedId(item.id)} aria-label={`Ver detalle de ${item.accion}`}><Eye size={18} /></button></td>
                </tr>
              ); })}</tbody>
            </table>
          </div>
          <PaginationBar pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : <Empty title="No hay registros para estos filtros" description="Pruebe con otro período o limpie la búsqueda." />}

      {selectedId && <Modal title="Detalle de auditoría" onClose={() => setSelectedId(null)} wide>
        {detail.isLoading ? <Loading /> : detail.error || !detail.data ? <ErrorBox message={apiError(detail.error)} /> : (
          <div className="audit-detail">
            <div className="audit-detail-summary"><CalendarClock /><div><strong>{detail.data.usuario}</strong><span>{dateParts(detail.data.fecha_hora).date} · {dateParts(detail.data.fecha_hora).time}</span></div></div>
            <dl><div><dt>Acción</dt><dd>{actionLabel(detail.data.accion)}</dd></div><div><dt>Entidad</dt><dd>{detail.data.entidad}</dd></div><div><dt>Descripción</dt><dd>{detail.data.detalle || "Operación registrada"}</dd></div><div><dt>Dirección IP</dt><dd>{detail.data.direccion_ip || "No disponible"}</dd></div></dl>
            {Boolean(detail.data.valores_anteriores || detail.data.valores_nuevos) && <div className="audit-changes"><article><h3>Valores anteriores</h3><pre>{JSON.stringify(detail.data.valores_anteriores ?? {}, null, 2)}</pre></article><article><h3>Valores nuevos</h3><pre>{JSON.stringify(detail.data.valores_nuevos ?? {}, null, 2)}</pre></article></div>}
          </div>
        )}
      </Modal>}
    </section>
  );
}
