import { Activity, BarChart3, CalendarDays, FolderTree, Image, LayoutDashboard, LogOut, Menu, Package, PanelLeftClose, PanelLeftOpen, ShieldCheck, Store, UserRound, Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { assetUrl } from "./api";
import { useAuth } from "./AuthContext";
import { FeedbackProvider } from "./ui";
import { SessionInactivityGuard } from "./SessionInactivityGuard";

const adminNav = [
  ["/gestion/admin/dashboard", "Resumen", LayoutDashboard],
  ["/gestion/admin/administradores", "Administradores", Users, "super"],
  ["/gestion/admin/expositores", "Expositores", Store],
  ["/gestion/admin/ferias", "Ferias", CalendarDays],
  ["/gestion/admin/productos", "Productos", Package],
  ["/gestion/admin/categorias", "Categorías", FolderTree],
  ["/gestion/admin/auditoria", "Auditoría", Activity],
  ["/gestion/admin/reportes", "Reportes", BarChart3],
  ["/gestion/admin/perfil", "Mi perfil", UserRound],
] as const;

const exhibitorNav = [
  ["/gestion/expositor/dashboard", "Mis productos", Package],
  ["/gestion/expositor/perfil", "Mi empresa", UserRound],
] as const;

export function InstitutionalSeal({ className = "" }: { className?: string }) {
  return <img className={`institutional-seal ${className}`.trim()} src="/escudo-bolivia.png" alt="Escudo del Estado Plurinacional de Bolivia" />;
}

export function PublicHeader() {
  return <header className="public-header"><div className="container public-header-content"><Link to="/catalogo" className="brand"><Store/> Catálogo Digital de Ferias</Link><Link to="/catalogo" className="header-seal-link" aria-label="Ir al catálogo"><InstitutionalSeal className="header-seal" /></Link><Link to="/gestion/login" className="btn-light">Portal de gestión</Link></div></header>;
}

export function ManagementLayout({ children, area }: { children: React.ReactNode; area: "admin" | "exhibitor" }) {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("catalog_sidebar_collapsed") === "true");
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = area === "admin" ? adminNav.filter((item) => item[3] !== "super" || user?.role === "SUPERADMIN") : exhibitorNav;
  const areaTitle = area === "exhibitor"
    ? "Mi empresa"
    : user?.role === "SUPERADMIN"
      ? "Superadministración"
      : "Panel administrativo";
  const roleLabel = user?.role === "SUPERADMIN"
    ? "Superadministrador"
    : user?.role === "ADMIN_VICEMINISTERIO"
      ? "Administrador"
      : "Expositor";
  useEffect(() => localStorage.setItem("catalog_sidebar_collapsed", String(collapsed)), [collapsed]);
  const signOut = async () => { await logout(); navigate("/gestion/login", { replace: true }); };
  return <FeedbackProvider><div className={`management-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
    <SessionInactivityGuard/>
    <header className="management-header"><div className="header-brand"><button className="mobile-menu" onClick={() => setOpen(true)} aria-label="Abrir menú"><Menu/></button><button className="sidebar-toggle" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expandir barra lateral" : "Comprimir barra lateral"} title={collapsed ? "Expandir menú" : "Comprimir menú"}>{collapsed ? <PanelLeftOpen/> : <PanelLeftClose/>}</button><strong>Catálogo Digital de Ferias</strong></div><InstitutionalSeal className="management-seal"/><div className="header-user"><Link className="header-profile-link" to={area === "admin" ? "/gestion/admin/perfil" : "/gestion/expositor/perfil"} title={area === "admin" ? "Abrir mi perfil" : "Abrir mi empresa"}>{user?.foto_perfil ? <img src={assetUrl(user.foto_perfil)} alt="Foto de perfil"/> : <span className="header-avatar">{user?.first_name?.charAt(0)}</span>}</Link><span className="header-user-copy"><strong>{user?.first_name}</strong><small>{roleLabel}</small></span><button onClick={signOut}><LogOut size={18}/> <span>Salir</span></button></div></header>
    {open && <button className="sidebar-scrim" onClick={() => setOpen(false)} aria-label="Cerrar menú"/>}
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}><button className="sidebar-close" onClick={() => setOpen(false)} aria-label="Cerrar"><X/></button><p className="sidebar-title">{area === "admin" ? <ShieldCheck/> : <Store/>}<span>{areaTitle}</span></p><nav>{links.map(([to, label, Icon]) => <NavLink key={to} to={to} title={collapsed ? label : undefined} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? "active" : ""}><Icon size={20}/><span>{label}</span></NavLink>)}</nav><Link className="catalog-link" to="/catalogo" title={collapsed ? "Ver catálogo público" : undefined}><Image size={19}/><span>Ver catálogo público</span></Link></aside>
    <main className="management-main"><div className="content-wrap">{children}</div></main>
  </div></FeedbackProvider>;
}
