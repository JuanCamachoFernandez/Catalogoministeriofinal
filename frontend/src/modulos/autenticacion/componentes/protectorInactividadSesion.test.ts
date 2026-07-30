import { describe, expect, it } from "vitest";
import { estadoInactividad, LOCK_AFTER_MS, LOGOUT_AFTER_MS } from "./ProtectorInactividadSesion";

describe("control de inactividad", () => {
  it("mantiene activa la sesión antes de dos minutos", () => {
    expect(estadoInactividad(LOCK_AFTER_MS - 1)).toBe("active");
  });

  it("bloquea desde dos minutos", () => {
    expect(estadoInactividad(LOCK_AFTER_MS)).toBe("locked");
  });

  it("expira al cumplir cinco minutos", () => {
    expect(estadoInactividad(LOGOUT_AFTER_MS)).toBe("expired");
  });
});
