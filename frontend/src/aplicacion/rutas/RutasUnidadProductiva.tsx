import { Navigate, Route } from "react-router-dom";
import { RutaUnidad } from "../../modulos/unidad-productiva/rutas/RutaUnidad";
import { paginaDiferida } from "./paginaDiferida";

const unitPages = () => import("../../modulos/unidad-productiva");
const PaginaPerfilUnidadProductiva = paginaDiferida(unitPages, "PaginaPerfilUnidadProductiva");
const PaginaSectoresUnidad = paginaDiferida(unitPages, "PaginaSectoresUnidad");
const PaginaProductos = paginaDiferida(unitPages, "PaginaProductos");

export const rutasUnidadProductiva = [
  <Route
    key="unit-root"
    path="/unidad-productiva"
    element={<Navigate to="/unidad-productiva/productos" replace />}
  />,
  <Route
    key="unit-profile"
    path="/unidad-productiva/perfil"
    element={<RutaUnidad><PaginaPerfilUnidadProductiva /></RutaUnidad>}
  />,
  <Route
    key="unit-sectors"
    path="/unidad-productiva/sectores"
    element={<RutaUnidad><PaginaSectoresUnidad /></RutaUnidad>}
  />,
  <Route
    key="unit-products"
    path="/unidad-productiva/productos"
    element={<RutaUnidad><PaginaProductos /></RutaUnidad>}
  />,
];
