import type { ReactNode } from "react";
import { RutaProtegida } from "../../autenticacion/contexto/ContextoAutenticacion";
import { DisenioGestion } from "../../../aplicacion/disenios/DisenioGestion";

export function RutaUnidad({ children }: { children: ReactNode }) {
  return (
    <RutaProtegida roles={["PRODUCTIVE_UNIT_RESPONSIBLE", "EXPOSITOR"]}>
      <DisenioGestion area="productive-unit">{children}</DisenioGestion>
    </RutaProtegida>
  );
}
