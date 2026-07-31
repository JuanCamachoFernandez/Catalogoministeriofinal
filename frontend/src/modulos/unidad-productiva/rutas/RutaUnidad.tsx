import type { ReactNode } from "react";
import { RutaProtegida } from "../../autenticacion/contexto/ContextoAutenticacion";
import { DisenioGestion } from "../../../aplicacion/disenios/DisenioGestion";
import { ROLES_UNIDAD_PRODUCTIVA } from "../../../compartido/autenticacion/roles";

export function RutaUnidad({ children }: { children: ReactNode }) {
  return (
    <RutaProtegida roles={ROLES_UNIDAD_PRODUCTIVA}>
      <DisenioGestion area="productive-unit">{children}</DisenioGestion>
    </RutaProtegida>
  );
}
