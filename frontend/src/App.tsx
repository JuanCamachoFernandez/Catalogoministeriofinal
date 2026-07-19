import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ProtectedRoute } from "./AuthContext";
import { ManagementLayout } from "./Layouts";
import { Loading } from "./ui";

const page = <T extends Record<string, unknown>, K extends keyof T>(
  loader: () => Promise<T>,
  name: K,
) =>
  lazy(() =>
    loader().then((module) => ({
      default: module[name] as React.ComponentType,
    })),
  );
const CatalogPage = page(() => import("./PublicPages"), "CatalogPage");
const FairDetailPage = page(() => import("./PublicPages"), "FairDetailPage");
const ExhibitorCatalogPage = page(
  () => import("./PublicPages"),
  "ExhibitorCatalogPage",
);
const NotFoundPage = page(() => import("./PublicPages"), "NotFoundPage");
const LoginPage = page(() => import("./AuthPages"), "LoginPage");
const ForgotPasswordPage = page(
  () => import("./AuthPages"),
  "ForgotPasswordPage",
);
const ResetPasswordPage = page(
  () => import("./AuthPages"),
  "ResetPasswordPage",
);
const ChangePasswordPage = page(
  () => import("./AuthPages"),
  "ChangePasswordPage",
);
const AdminDashboard = page(() => import("./AdminPortal"), "AdminDashboard");
const AdministratorsPage = page(
  () => import("./AdminPortal"),
  "AdministratorsPage",
);
const ExhibitorsPage = page(() => import("./AdminPortal"), "ExhibitorsPage");
const FairsPage = page(() => import("./AdminPortal"), "FairsPage");
const ProductsPage = page(() => import("./AdminPortal"), "ProductsPage");
const CategoriesPage = page(() => import("./AdminPortal"), "CategoriesPage");
const AuditPage = page(() => import("./AdminPortal"), "AuditPage");
const ReportsPage = page(() => import("./ReportsPage"), "ReportsPage");
const AdminProfilePage = page(() => import("./AdminProfilePage"), "AdminProfilePage");
const ExhibitorProductsPage = page(
  () => import("./ExhibitorPortal"),
  "ExhibitorProductsPage",
);
const ExhibitorProfilePage = page(
  () => import("./ExhibitorPortal"),
  "ExhibitorProfilePage",
);

const adminRoles = ["SUPERADMIN", "ADMIN_VICEMINISTERIO"] as const;
function AdminRoute({
  children,
  superOnly = false,
}: {
  children: React.ReactNode;
  superOnly?: boolean;
}) {
  return (
    <ProtectedRoute roles={superOnly ? ["SUPERADMIN"] : [...adminRoles]}>
      <ManagementLayout area="admin">{children}</ManagementLayout>
    </ProtectedRoute>
  );
}
function ExhibitorRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute roles={["EXPOSITOR"]}>
      <ManagementLayout area="exhibitor">{children}</ManagementLayout>
    </ProtectedRoute>
  );
}

function RouteTitle() {
  const { pathname } = useLocation();
  useEffect(() => {
    const labels: Record<string, string> = {
      "/catalogo": "Catálogo de la feria",
      "/gestion/login": "Iniciar sesión",
      "/gestion/admin/dashboard": "Resumen administrativo",
      "/gestion/admin/administradores": "Administradores",
      "/gestion/admin/expositores": "Expositores",
      "/gestion/admin/ferias": "Ferias",
      "/gestion/admin/productos": "Productos",
      "/gestion/admin/categorias": "Categorías",
      "/gestion/admin/auditoria": "Auditoría",
      "/gestion/admin/perfil": "Mi perfil",
      "/gestion/expositor/dashboard": "Mis productos",
      "/gestion/expositor/perfil": "Mi empresa",
    };
    const pageLabel =
      labels[pathname] ??
      (pathname.startsWith("/catalogo/")
        ? "Productos del expositor"
        : "Catálogo Digital");
    const description = pathname.startsWith("/catalogo")
      ? "Conozca las ferias publicadas, sus expositores y productos bolivianos."
      : "Portal de gestión del Catálogo Digital de Ferias.";
    document.title = `${pageLabel} | Ferias`;
    const setMeta = (selector: string, attribute: string, value: string) => {
      const element = document.head.querySelector<HTMLMetaElement>(selector);
      element?.setAttribute(attribute, value);
    };
    setMeta('meta[name="description"]', "content", description);
    setMeta('meta[property="og:title"]', "content", document.title);
    setMeta('meta[property="og:description"]', "content", description);
    const canonical = document.head.querySelector<HTMLLinkElement>(
      'link[rel="canonical"]',
    );
    canonical?.setAttribute("href", window.location.href);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <>
      <RouteTitle />
      <Suspense fallback={<Loading label="Cargando página…" />}>
        <Routes>
          <Route path="/" element={<Navigate to="/catalogo" replace />} />
          <Route path="/catalogo" element={<CatalogPage />} />
          <Route path="/catalogo/ferias/:slug" element={<FairDetailPage />} />
          <Route
            path="/catalogo/ferias/:slug/expositores/:exhibitorId"
            element={<ExhibitorCatalogPage />}
          />
          <Route path="/gestion/login" element={<LoginPage />} />
          <Route
            path="/gestion/recuperar-contrasena"
            element={<ForgotPasswordPage />}
          />
          <Route
            path="/gestion/restablecer-contrasena"
            element={<ResetPasswordPage />}
          />
          <Route
            path="/gestion/cambiar-contrasena"
            element={
              <ProtectedRoute>
                <ChangePasswordPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/gestion/admin/dashboard"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/administradores"
            element={
              <AdminRoute superOnly>
                <AdministratorsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/expositores"
            element={
              <AdminRoute>
                <ExhibitorsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/ferias"
            element={
              <AdminRoute>
                <FairsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/productos"
            element={
              <AdminRoute>
                <ProductsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/categorias"
            element={
              <AdminRoute>
                <CategoriesPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/auditoria"
            element={
              <AdminRoute>
                <AuditPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/reportes"
            element={
              <AdminRoute>
                <ReportsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/admin/perfil"
            element={
              <AdminRoute>
                <AdminProfilePage />
              </AdminRoute>
            }
          />
          <Route
            path="/gestion/expositor/dashboard"
            element={
              <ExhibitorRoute>
                <ExhibitorProductsPage />
              </ExhibitorRoute>
            }
          />
          <Route
            path="/gestion/expositor/perfil"
            element={
              <ExhibitorRoute>
                <ExhibitorProfilePage />
              </ExhibitorRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </>
  );
}
