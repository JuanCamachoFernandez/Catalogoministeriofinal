import { describe, expect, it } from "vitest";
import {
  ROLES_USUARIO,
  puedeAccederFuncionAdministracion,
  inicioParaRol,
  esRolAdministracion,
  esRolUnidadProductiva,
} from "./roles";

describe("politicas de roles del frontend", () => {
  it("clasifica portales y rutas iniciales", () => {
    expect(esRolAdministracion(ROLES_USUARIO.ADMIN)).toBe(true);
    expect(esRolUnidadProductiva(ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE)).toBe(true);
    expect(inicioParaRol(ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE)).toBe(
      "/unidad-productiva/productos",
    );
    expect(inicioParaRol(ROLES_USUARIO.ADMIN)).toBe("/admin");
  });

  it("habilita las funciones administrativas canonicas", () => {
    expect(
      puedeAccederFuncionAdministracion(
        ROLES_USUARIO.ADMIN,
        "administrator-accounts",
      ),
    ).toBe(true);
    expect(
      puedeAccederFuncionAdministracion(ROLES_USUARIO.ADMIN, "reports"),
    ).toBe(true);
  });
});
