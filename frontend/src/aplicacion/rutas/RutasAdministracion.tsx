import type { ReactNode } from "react";
import { Route } from "react-router-dom";
import { DisenioGestion } from "../disenios/DisenioGestion";
import { RutaProtegida } from "../../modulos/autenticacion/contexto/ContextoAutenticacion";
import {
  rolesParaFuncionAdministracion,
  type FuncionAdministracion,
} from "../../compartido/autenticacion/roles";
import { paginaDiferida } from "./paginaDiferida";
import "../../modulos/registro/estilos/registro.css";
import "../../modulos/administracion/estilos/administracion.css";

const PaginaInicioAdministracion = paginaDiferida(() => import("../../modulos/administracion/paginas/PaginaResumen"), "PaginaInicioAdministracion");
const PaginaSolicitudesRegistro = paginaDiferida(
  () => import("../../modulos/administracion/paginas/PaginaSolicitudesRegistro"),
  "default",
);
const PaginaUnidadesProductivas = paginaDiferida(
  () => import("../../modulos/administracion/paginas/PaginaUnidadesProductivas"),
  "default",
);
const PaginaSectoresProductivos = paginaDiferida(
  () => import("../../modulos/administracion/paginas/PaginaSectoresProductivos"),
  "default",
);
const PaginaProductosAdministracion = paginaDiferida(
  () => import("../../modulos/administracion/paginas/PaginaProductosAdministracion"),
  "default",
);
const PaginaFerias = paginaDiferida(() => import("../../modulos/administracion/paginas/PaginaFerias"), "default");
const PaginaAdministradores = paginaDiferida(
  () => import("../../modulos/administracion/paginas/PaginaAdministradores"),
  "default",
);
const PaginaAuditoria = paginaDiferida(() => import("../../modulos/administracion/paginas/PaginaAuditoria"), "PaginaAuditoria");
const PaginaPerfilAdmin = paginaDiferida(
  () => import("../../modulos/administracion/paginas/PaginaPerfilAdmin"),
  "default",
);

function AdminRoute({
  feature,
  children,
}: {
  feature: FuncionAdministracion;
  children: ReactNode;
}) {
  return (
    <RutaProtegida roles={rolesParaFuncionAdministracion(feature)}>
      <DisenioGestion area="admin">
        <div className="admin-area">{children}</div>
      </DisenioGestion>
    </RutaProtegida>
  );
}

const route = (path: string, feature: FuncionAdministracion, element: ReactNode) => (
  <Route
    key={path}
    path={path}
    element={<AdminRoute feature={feature}>{element}</AdminRoute>}
  />
);

export const rutasAdministracion = [
  route("/admin", "dashboard", <PaginaInicioAdministracion />),
  route("/admin/solicitudes", "registration-requests", <PaginaSolicitudesRegistro />),
  route("/admin/unidades-productivas", "productive-units", <PaginaUnidadesProductivas />),
  route("/admin/sectores-productivos", "productive-sectors", <PaginaSectoresProductivos />),
  route("/admin/productos", "products", <PaginaProductosAdministracion />),
  route("/admin/ferias", "fairs", <PaginaFerias />),
  route("/admin/administradores", "administrator-accounts", <PaginaAdministradores />),
  route("/admin/auditoria", "audit", <PaginaAuditoria />),
  route("/admin/perfil", "dashboard", <PaginaPerfilAdmin />),
];
