import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarClock,
  CalendarDays,
  CircleAlert,
  ClipboardCheck,
  Factory,
  FilePlus2,
  History,
  MapPin,
  PackageCheck,
  UsersRound,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api, apiError, type AuditItem } from "./api";
import { auditActionLabel, auditDescriptionLabel, auditEntityLabel } from "./auditLabels";
import { Empty, ErrorBox, Loading, StatusBadge } from "./ui";

type DashboardResponse = {
  stats: {
    ferias: number;
    ferias_publicadas: number;
    productos: number;
    productos_disponibles: number;
    productos_sin_stock: number;
    unidades_productivas: number;
    unidades_productivas_activas: number;
    solicitudes_pendientes: number;
    solicitudes_ultimos_30_dias: number;
    participaciones_pendientes: number;
  };
  proxima_feria: {
    id: string;
    nombre: string;
    ubicacion: string;
    fecha_inicio: string;
    fecha_fin: string;
    estado: string;
    en_curso: boolean;
    dias_restantes: number;
  } | null;
  unidades_por_departamento: Array<{
    departamento: string;
    cantidad: number;
  }>;
  recent_audits: AuditItem[];
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

const formatFairDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));

export function AdminHomePage() {
  const dashboard = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: () => api.get<DashboardResponse>("/admin/dashboard").then((response) => response.data),
  });

  if (dashboard.isLoading) return <Loading label="Preparando el panel…" />;
  if (dashboard.error || !dashboard.data) {
    return <ErrorBox message={apiError(dashboard.error, "No se pudo cargar el panel administrativo.")} />;
  }

  const {
    stats,
    proxima_feria: nextFair,
    unidades_por_departamento: unitsByDepartment,
    recent_audits: audits,
  } = dashboard.data;
  const cards = [
    { label: "Unidades Productivas", value: stats.unidades_productivas, detail: `${stats.unidades_productivas_activas} activas`, icon: Factory, to: "/admin/unidades-productivas" },
    { label: "Solicitudes pendientes", value: stats.solicitudes_pendientes, detail: "Requieren revisión", icon: ClipboardCheck, to: "/admin/solicitudes" },
    { label: "Ferias registradas", value: stats.ferias, detail: `${stats.ferias_publicadas} en curso`, icon: CalendarDays, to: "/admin/ferias" },
    { label: "Productos", value: stats.productos, detail: `${stats.productos_disponibles} disponibles`, icon: PackageCheck, to: "/admin/productos" },
  ];
  const percentage = (value: number, total: number) =>
    total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
  const health = [
    { label: "Unidades activas", value: stats.unidades_productivas_activas, total: stats.unidades_productivas },
    { label: "Productos disponibles", value: stats.productos_disponibles, total: stats.productos },
    { label: "Ferias publicadas", value: stats.ferias_publicadas, total: stats.ferias },
  ];
  const attention = [
    { label: "Solicitudes por revisar", value: stats.solicitudes_pendientes, to: "/admin/solicitudes" },
    { label: "Participaciones pendientes", value: stats.participaciones_pendientes, to: "/admin/ferias" },
    { label: "Productos sin stock", value: stats.productos_sin_stock, to: "/admin/productos" },
  ];
  const largestDepartment = Math.max(...unitsByDepartment.map((item) => item.cantidad), 1);
  const fairCountdown = nextFair
    ? nextFair.en_curso
      ? nextFair.dias_restantes === 0 ? "Finaliza hoy" : `${nextFair.dias_restantes} ${nextFair.dias_restantes === 1 ? "día" : "días"} para finalizar`
      : nextFair.dias_restantes === 0 ? "Comienza hoy" : `${nextFair.dias_restantes} ${nextFair.dias_restantes === 1 ? "día" : "días"} para comenzar`
    : "";

  return (
    <section className="admin-dashboard">
      <header className="page-heading dashboard-heading">
        <div>
          <span className="eyebrow">Administración</span>
          <h1>Resumen</h1>
          <p>Una vista breve del catálogo y de las tareas que necesitan atención.</p>
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

      <div className="dashboard-overview">
        <article className="panel dashboard-health-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">Cobertura</span><h2>Estado operativo</h2></div>
          </div>
          <div className="dashboard-health-list">
            {health.map((item) => {
              const progress = percentage(item.value, item.total);
              return (
                <div className="dashboard-health-item" key={item.label}>
                  <div><span>{item.label}</span><small>{item.value} de {item.total}</small></div>
                  <span className="dashboard-progress" role="progressbar" aria-label={item.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
                    <i style={{ width: `${progress}%` }} />
                  </span>
                  <span className="dashboard-percentage">{progress}%</span>
                </div>
              );
            })}
          </div>
        </article>

        <aside className="panel dashboard-attention-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">Pendientes</span><h2>Requiere atención</h2></div>
            <CircleAlert size={20} aria-hidden="true" />
          </div>
          <div className="dashboard-attention-list">
            {attention.map((item) => (
              <Link to={item.to} key={item.label}>
                <span>{item.label}</span>
                <span className={item.value > 0 ? "attention-count has-items" : "attention-count"}>{item.value}</span>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            ))}
          </div>
        </aside>
      </div>

      <div className="dashboard-context">
        <Link className="panel dashboard-next-fair" to="/admin/ferias">
          <span className="dashboard-context-icon"><CalendarClock /></span>
          <div>
            <span className="eyebrow">Agenda</span>
            <h2>Próxima feria</h2>
            {nextFair ? (
              <>
                <p>{nextFair.nombre}</p>
                <small><MapPin />{nextFair.ubicacion}</small>
                <small>{formatFairDate(nextFair.fecha_inicio)} — {formatFairDate(nextFair.fecha_fin)}</small>
                <span className="dashboard-countdown">{fairCountdown}</span>
              </>
            ) : <p className="dashboard-muted">No hay ferias próximas programadas.</p>}
          </div>
          <ArrowRight className="dashboard-context-arrow" size={17} />
        </Link>

        <Link className="panel dashboard-monthly-requests" to="/admin/solicitudes">
          <span className="dashboard-context-icon"><FilePlus2 /></span>
          <div>
            <span className="eyebrow">Últimos 30 días</span>
            <strong>{stats.solicitudes_ultimos_30_dias}</strong>
            <p>Solicitudes recibidas</p>
            <small>Incluye todos los estados</small>
          </div>
          <ArrowRight className="dashboard-context-arrow" size={17} />
        </Link>

        <article className="panel dashboard-departments">
          <div className="panel-heading">
            <div><span className="eyebrow">Cobertura nacional</span><h2>Unidades por departamento</h2></div>
            <MapPin size={20} aria-hidden="true" />
          </div>
          {unitsByDepartment.length ? (
            <div className="dashboard-department-list">
              {unitsByDepartment.map((item) => (
                <div key={item.departamento}>
                  <span>{item.departamento}</span>
                  <span className="dashboard-department-bar" aria-hidden="true">
                    <i style={{ width: `${(item.cantidad / largestDepartment) * 100}%` }} />
                  </span>
                  <small>{item.cantidad}</small>
                </div>
              ))}
            </div>
          ) : <p className="dashboard-muted">Todavía no hay unidades registradas.</p>}
        </article>
      </div>

      <article className="panel dashboard-audit-panel">
        <div className="panel-heading">
          <div><span className="eyebrow">Cambios relevantes</span><h2>Actividad administrativa reciente</h2></div>
          <Link className="link-arrow" to="/admin/auditoria">Ver historial completo <ArrowRight size={15} /></Link>
        </div>
          {audits.length ? (
            <div className="audit-feed">
              {audits.map((item) => (
                <article key={item.id}>
                  <span className="audit-avatar"><UsersRound size={18} /></span>
                  <div>
                    <div className="audit-feed-title">
                      <span className="audit-user">{item.usuario ?? "Sistema"}</span>
                      <StatusBadge value={item.accion} />
                      <span className="audit-action-mobile">{auditActionLabel(item.accion)}</span>
                    </div>
                    <p>{auditDescriptionLabel(item.descripcion)}</p>
                    <small>{auditEntityLabel(item.entidad)} · {formatDate(item.created_at)}</small>
                  </div>
                </article>
              ))}
            </div>
          ) : <Empty title="Todavía no hay actividad registrada" />}
      </article>
    </section>
  );
}
