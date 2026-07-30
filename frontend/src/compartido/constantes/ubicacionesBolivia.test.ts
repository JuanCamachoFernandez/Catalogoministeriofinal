import { describe, expect, it } from "vitest";
import {
  BOLIVIA_DEPARTMENTS,
  BOLIVIA_MUNICIPALITIES,
  municipiosPara,
} from "./ubicacionesBolivia";

describe("catálogo territorial de Bolivia", () => {
  it("incluye los nueve departamentos", () => {
    expect(BOLIVIA_DEPARTMENTS).toHaveLength(9);
  });

  it("relaciona municipios con su departamento", () => {
    expect(municipiosPara("La Paz")).toContain("El Alto");
    expect(municipiosPara("Santa Cruz")).toContain(
      "Santa Cruz de la Sierra",
    );
  });

  it("contiene el catálogo nacional de municipios y AIOC", () => {
    const total = Object.values(BOLIVIA_MUNICIPALITIES).reduce(
      (sum, items) => sum + items.length,
      0,
    );
    expect(total).toBeGreaterThanOrEqual(339);
  });
});
