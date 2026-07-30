import { Navigate, Route } from "react-router-dom";

export const rutasRedireccionAnteriores = [
  <Route key="legacy-login" path="/gestion/login" element={<Navigate to="/login" replace />} />,
  <Route key="legacy-forgot" path="/gestion/recuperar-password" element={<Navigate to="/olvide-password" replace />} />,
  <Route key="legacy-reset" path="/gestion/restablecer-password" element={<Navigate to="/restablecer-password" replace />} />,
  <Route key="legacy-change" path="/gestion/cambiar-password" element={<Navigate to="/cambiar-password" replace />} />,
  <Route key="legacy-admin" path="/gestion/admin/*" element={<Navigate to="/admin" replace />} />,
  <Route key="legacy-exhibitor" path="/gestion/expositor/*" element={<Navigate to="/unidad-productiva" replace />} />,
];
