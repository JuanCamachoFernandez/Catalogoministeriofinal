import { describe, expect, it } from "vitest";
import type { CanonicalFair } from "../../../compartido";
import { colorPrecioEvento } from "./temaEvento";

describe("tema visual del evento", () => {
  it("usa el color visualmente más oscuro de la paleta para los precios", () => {
    const fair = {
      tipo: "EVENT",
      color_primario: "#D34A38",
      color_secundario: "#F0B429",
      color_terciario: "#173F5F",
    } as CanonicalFair;

    expect(colorPrecioEvento(fair)).toBe("#173F5F");
  });
});
