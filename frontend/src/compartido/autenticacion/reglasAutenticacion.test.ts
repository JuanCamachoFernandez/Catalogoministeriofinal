import { describe, expect, it } from "vitest";
import { inicioParaRol } from "./roles";
import { esContrasenaSegura } from "../validaciones/contrasena";

describe("reglas de autenticacion", () => {
  it("envia administradores al panel administrativo", () => {
    expect(inicioParaRol("ADMIN")).toBe("/admin");
  });

  it("envia responsables a su panel", () => {
    expect(inicioParaRol("PRODUCTIVE_UNIT_RESPONSIBLE")).toBe(
      "/unidad-productiva/productos",
    );
  });

  it("valida todos los requisitos de contrasena", () => {
    expect(esContrasenaSegura("Segura2026!")).toBe(true);
    expect(esContrasenaSegura("sinSimbolo2026")).toBe(false);
    expect(esContrasenaSegura("Corta1!")).toBe(false);
  });
});
