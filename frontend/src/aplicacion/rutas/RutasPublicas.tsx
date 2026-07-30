import { Route } from "react-router-dom";
import { paginaDiferida } from "./paginaDiferida";

const publicPages = () => import("../../modulos/catalogo-publico");
const registrationPage = () =>
  import("../../modulos/registro/paginas/PaginaRegistro");

const PaginaCatalogoPublico = paginaDiferida(publicPages, "PaginaCatalogoPublico");
const PaginaFeriaPublica = paginaDiferida(publicPages, "PaginaFeriaPublica");
const PaginaUnidadPublica = paginaDiferida(publicPages, "PaginaUnidadPublica");
const PaginaRegistro = paginaDiferida(registrationPage, "PaginaRegistro");

export const rutasPublicas = [
  <Route key="catalog" path="/catalogo" element={<PaginaCatalogoPublico />} />,
  <Route
    key="public-fair"
    path="/catalogo/ferias/:fairId"
    element={<PaginaFeriaPublica />}
  />,
  <Route
    key="public-unit"
    path="/catalogo/ferias/:fairId/unidades/:unitId"
    element={<PaginaUnidadPublica />}
  />,
  <Route
    key="registration"
    path="/solicitud-registro"
    element={<PaginaRegistro />}
  />,
];
