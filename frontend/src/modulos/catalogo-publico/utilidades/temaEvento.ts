import type { CSSProperties } from "react";
import type { CanonicalFair } from "../../../compartido";

export function esEventoTematico(fair?: CanonicalFair | null): fair is CanonicalFair {
  return Boolean(fair && fair.tipo === "EVENT");
}

export function clasesTemaEvento(fair?: CanonicalFair | null) {
  if (!esEventoTematico(fair)) return "";
  return (fair.animaciones_tema ?? [])
    .map((animation) => `event-animation-${animation.toLowerCase()}`)
    .join(" ");
}

function luminosidadHex(color: string) {
  const value = color.replace("#", "");
  if (!/^[0-9a-f]{6}$/i.test(value)) return Number.POSITIVE_INFINITY;
  const channels = [0, 2, 4].map((index) => {
    const channel = Number.parseInt(value.slice(index, index + 2), 16) / 255;
    return channel <= 0.04045
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

export function colorPrecioEvento(fair?: CanonicalFair | null) {
  if (!esEventoTematico(fair)) return "#176b3a";
  return [fair.color_primario, fair.color_secundario, fair.color_terciario]
    .filter((color): color is string => Boolean(color))
    .sort((left, right) => luminosidadHex(left) - luminosidadHex(right))[0] ?? "#243b32";
}

export function variablesTemaEvento(
  fair?: CanonicalFair | null,
): CSSProperties | undefined {
  if (!esEventoTematico(fair)) return undefined;
  return {
    "--event-color-1": fair.color_primario ?? "#24453a",
    "--event-color-2": fair.color_secundario ?? "#4f7c67",
    "--event-color-3": fair.color_terciario ?? "#c5964a",
    "--event-price-color": colorPrecioEvento(fair),
  } as CSSProperties;
}
