import { Route } from "react-router-dom";
import { RutaProtegida } from "../../modulos/autenticacion/contexto/ContextoAutenticacion";
import { paginaDiferida } from "./paginaDiferida";

const authPages = () => import("../../modulos/autenticacion/paginas/PaginasAutenticacion");
const PaginaInicioSesion = paginaDiferida(authPages, "PaginaInicioSesion");
const PaginaRecuperarContrasena = paginaDiferida(authPages, "PaginaRecuperarContrasena");
const PaginaRestablecerContrasena = paginaDiferida(authPages, "PaginaRestablecerContrasena");
const PaginaCambiarContrasena = paginaDiferida(authPages, "PaginaCambiarContrasena");

export const rutasAutenticacion = [
  <Route key="login" path="/login" element={<PaginaInicioSesion />} />,
  <Route
    key="forgot-password"
    path="/olvide-password"
    element={<PaginaRecuperarContrasena />}
  />,
  <Route
    key="reset-password"
    path="/restablecer-password"
    element={<PaginaRestablecerContrasena />}
  />,
  <Route
    key="change-password"
    path="/cambiar-password"
    element={
      <RutaProtegida>
        <PaginaCambiarContrasena />
      </RutaProtegida>
    }
  />,
];
