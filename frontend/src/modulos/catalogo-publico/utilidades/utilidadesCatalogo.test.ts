import { describe, expect, it } from "vitest";
import { construirItemsWhatsapp, formatearFechaBoliviana, formatearBolivianos } from "./utilidadesCatalogo";

describe("utilidades del catálogo", () => {
  it("convierte la selección en el contrato de WhatsApp", () => {
    expect(construirItemsWhatsapp({ productoA: 2, productoB: 1 })).toEqual([
      { product_id: "productoA", quantity: 2 },
      { product_id: "productoB", quantity: 1 },
    ]);
  });

  it("descarta cantidades inválidas", () => {
    expect(construirItemsWhatsapp({ correcto: 3, cero: 0, decimal: 1.5, negativo: -1 })).toEqual([
      { product_id: "correcto", quantity: 3 },
    ]);
  });

  it("formatea fechas sin desplazarlas por zona horaria", () => {
    expect(formatearFechaBoliviana("2026-07-17")).toContain("2026");
  });

  it("explica cuando el producto no tiene precio", () => {
    expect(formatearBolivianos(null)).toBe("Consultar precio");
  });
});
