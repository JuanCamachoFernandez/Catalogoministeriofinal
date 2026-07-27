import { CalendarDays } from "lucide-react";
import { assetUrl, type CanonicalFair } from "../../api";

export function FairImage({ fair }: { fair: CanonicalFair }) {
  return fair.imagen_portada ? (
    <img
      className="card-media"
      src={assetUrl(fair.imagen_portada)}
      alt={`Portada de ${fair.nombre}`}
    />
  ) : (
    <div className="card-media image-placeholder">
      <CalendarDays />
      <span>Feria productiva</span>
    </div>
  );
}
