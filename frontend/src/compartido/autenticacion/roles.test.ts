import { describe, expect, it } from "vitest";
import {
  ROLES_USUARIO,
  puedeAccederFuncionAdministracion,
  rolCanonicoPara,
  inicioParaRol,
  esRolAdministracion,
  esRolUnidadProductiva,
} from "./roles";

describe("políticas de roles del frontend", () => {
  it("mantiene compatibilidad entre roles canónicos y heredados", () => {
    expect(rolCanonicoPara(ROLES_USUARIO.SUPERADMIN)).toBe(ROLES_USUARIO.ADMIN);
    expect(rolCanonicoPara(ROLES_USUARIO.ADMIN_VICEMINISTERIO)).toBe(ROLES_USUARIO.ADMIN);
    expect(rolCanonicoPara(ROLES_USUARIO.EXPOSITOR)).toBe(
      ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE,
    );
  });

  it("clasifica portales y rutas iniciales", () => {
    expect(esRolAdministracion(ROLES_USUARIO.ADMIN)).toBe(true);
    expect(esRolUnidadProductiva(ROLES_USUARIO.EXPOSITOR)).toBe(true);
    expect(inicioParaRol(ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE)).toBe(
      "/unidad-productiva/productos",
    );
    expect(inicioParaRol(ROLES_USUARIO.SUPERADMIN)).toBe("/admin");
  });

  it("no concede reportes ni cuentas por pertenecer genéricamente al portal", () => {
    expect(
      puedeAccederFuncionAdministracion(ROLES_USUARIO.ADMIN_VICEMINISTERIO, "administrator-accounts"),
    ).toBe(false);
    expect(puedeAccederFuncionAdministracion(ROLES_USUARIO.ADMIN, "reports")).toBe(false);
    expect(puedeAccederFuncionAdministracion(ROLES_USUARIO.SUPERADMIN, "reports")).toBe(true);
  });
});
