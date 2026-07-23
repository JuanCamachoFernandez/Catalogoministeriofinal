import { useQuery } from "@tanstack/react-query";
import {
  CalendarDays,
  ClipboardCheck,
  Factory,
  History,
  PackageCheck,
  UsersRound,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api, apiError, type AuditItem } from "./api";
import { Empty, ErrorBox, Loading, StatusBadge } from "./ui";

type DashboardResponse = {
  stats: {
    ferias: number;
    ferias_publicadas: number;
    productos: number;
    productos_disponibles: number;
    unidades_productivas: number;
    unidades_productivas_activas: number;
    solicitudes_pendientes: number;
    participaciones_pendientes: number;
  };
  recent_audits: AuditItem[];
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

export function AdminHomePage() {
  const dashboard = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: () => api.get<DashboardResponse>("/admin/dashboard").then((response) => response.data),
  });

  if (dashboard.isLoading) return <Loading label="Preparando el panel…" />;
  if (dashboard.error || !dashboard.data) {
    return <ErrorBox message={apiError(dashboard.error, "No se pudo cargar el panel administrativo.")} />;
  }

  const { stats, recent_audits: audits } = dashboard.data;
  const cards = [
    { label: "Unidades Productivas", value: stats.unidades_productivas, detail: `${stats.unidades_productivas_activas} activas`, icon: Factory, to: "/admin/unidades-productivas" },
    { label: "Solicitudes pendientes", value: stats.solicitudes_pendientes, detail: "Requieren revisión", icon: ClipboardCheck, to: "/admin/solicitudes" },
    { label: "Ferias registradas", value: stats.ferias, detail: `${stats.ferias_publicadas} en curso`, icon: CalendarDays, to: "/admin/ferias" },
    { label: "Productos", value: stats.productos, detail: `${stats.productos_disponibles} disponibles`, icon: PackageCheck, to: "/admin/productos" },
  ];

  return (
    <section>
      <header className="page-heading dashboard-heading">
        <div>
          <span className="eyebrow">Panel general</span>
          <h1>Resumen administrativo</h1>
          <p>Estado actual del catálogo, las ferias y las Unidades Productivas.</p>
        </div>
        <Link className="btn-outline" to="/admin/auditoria">
          <History size={18} /> Ver auditoría
        </Link>
      </header>

      <div className="dashboard-stats">
        {cards.map(({ label, value, detail, icon: Icon, to }) => (
          <Link className="dashboard-stat" to={to} key={label}>
            <span className="dashboard-stat-icon"><Icon /></span>
            <div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div>
          </Link>
        ))}
      </div>

      <div className="dashboard-layout">
        <article className="panel dashboard-audit-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">Trazabilidad</span><h2>Actividad reciente</h2></div>
            <Link className="link-arrow" to="/admin/auditoria">Ver historial completo →</Link>
          </div>
          {audits.length ? (
            <div className="audit-feed">
              {audits.map((item) => (
                <article key={item.id}>
                  <span className="audit-avatar"><UsersRound size={18} /></span>
                  <div>
                    <div className="audit-feed-title"><strong>{item.usuario ?? "Sistema"}</strong><StatusBadge value={item.accion} /></div>
                    <p>{item.descripcion}</p>
                    <small>{item.entidad} · {formatDate(item.created_at)}</small>
                  </div>
                </article>
              ))}
            </div>
          ) : <Empty title="Todavía no hay actividad registrada" />}
        </article>

        <aside className="panel quick-panel">
          <span className="eyebrow">Accesos rápidos</span>
          <h2>Gestión diaria</h2>
          <Link to="/admin/solicitudes"><ClipboardCheck /><span><strong>Revisar solicitudes</strong><small>Aprobar o solicitar correcciones</small></span></Link>
          <Link to="/admin/ferias"><CalendarDays /><span><strong>Gestionar ferias</strong><small>Fechas y participaciones</small></span></Link>
          <Link to="/admin/unidades-productivas"><Factory /><span><strong>Ver expositoras</strong><small>Directorio de unidades</small></span></Link>
          {stats.participaciones_pendientes > 0 && <p className="quick-alert">Hay {stats.participaciones_pendientes} participaciones pendientes.</p>}
        </aside>
      </div>
    </section>
  );
}
