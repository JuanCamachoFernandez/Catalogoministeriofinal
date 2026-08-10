import { CalendarDays } from "lucide-react";
import { urlRecurso, type CanonicalFair } from "../../../compartido";
import {
  clasesTemaEvento,
  esEventoTematico,
  variablesTemaEvento,
} from "../utilidades/temaEvento";

export function ImagenFeria({ fair }: { fair: CanonicalFair }) {
  return fair.imagen_portada ? (
    <img
      className={`card-media${esEventoTematico(fair) ? " event-themed-media" : ""} ${clasesTemaEvento(fair)}`.trim()}
      style={variablesTemaEvento(fair)}
      src={urlRecurso(fair.imagen_portada)}
      alt={`Portada de ${fair.nombre}`}
    />
  ) : (
    <div
      className={`card-media image-placeholder${esEventoTematico(fair) ? " event-themed-placeholder" : ""} ${clasesTemaEvento(fair)}`.trim()}
      style={variablesTemaEvento(fair)}
    >
      <CalendarDays />
      <span>{fair.tipo === "EVENT" ? "Evento productivo" : "Feria productiva"}</span>
    </div>
  );
}
