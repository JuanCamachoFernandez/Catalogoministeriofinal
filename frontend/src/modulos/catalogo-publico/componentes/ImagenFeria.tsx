import { CalendarDays } from "lucide-react";
import { urlRecurso, type CanonicalFair } from "../../../compartido";

export function ImagenFeria({ fair }: { fair: CanonicalFair }) {
  return fair.imagen_portada ? (
    <img
      className="card-media"
      src={urlRecurso(fair.imagen_portada)}
      alt={`Portada de ${fair.nombre}`}
    />
  ) : (
    <div className="card-media image-placeholder">
      <CalendarDays />
      <span>Feria productiva</span>
    </div>
  );
}
