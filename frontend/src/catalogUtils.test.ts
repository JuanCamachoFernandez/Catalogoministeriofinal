import { describe, expect, it } from "vitest";
import { buildWhatsappItems, formatBolivianDate, formatBolivianos } from "./catalogUtils";

describe("utilidades del catálogo", () => {
  it("convierte la selección en el contrato de WhatsApp", () => {
    expect(buildWhatsappItems({ productoA: 2, productoB: 1 })).toEqual([
      { product_id: "productoA", quantity: 2 },
      { product_id: "productoB", quantity: 1 },
    ]);
  });

  it("descarta cantidades inválidas", () => {
    expect(buildWhatsappItems({ correcto: 3, cero: 0, decimal: 1.5, negativo: -1 })).toEqual([
      { product_id: "correcto", quantity: 3 },
    ]);
  });

  it("formatea fechas sin desplazarlas por zona horaria", () => {
    expect(formatBolivianDate("2026-07-17")).toContain("2026");
  });

  it("explica cuando el producto no tiene precio", () => {
    expect(formatBolivianos(null)).toBe("Consultar precio");
  });
});
