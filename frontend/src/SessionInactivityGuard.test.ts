import { describe, expect, it } from "vitest";
import { inactivityStatus, LOCK_AFTER_MS, LOGOUT_AFTER_MS } from "./SessionInactivityGuard";

describe("control de inactividad", () => {
  it("mantiene activa la sesión antes de dos minutos", () => {
    expect(inactivityStatus(LOCK_AFTER_MS - 1)).toBe("active");
  });

  it("bloquea desde dos minutos", () => {
    expect(inactivityStatus(LOCK_AFTER_MS)).toBe("locked");
  });

  it("expira al cumplir cinco minutos", () => {
    expect(inactivityStatus(LOGOUT_AFTER_MS)).toBe("expired");
  });
});
