import { describe, expect, it } from "vitest";
import { etiquetaAccionAuditoria, etiquetaDescripcionAuditoria, etiquetaEntidadAuditoria } from "./etiquetasAuditoria";

describe("etiquetas de auditoría", () => {
  it("presenta las acciones con espacios y tildes", () => {
    expect(etiquetaAccionAuditoria("RESTABLECER_CONTRASENA")).toBe("Restablecer contraseña");
    expect(etiquetaAccionAuditoria("INTENTO_RECUPERACION_FALLIDO")).toBe("Intento de recuperación fallido");
    expect(etiquetaAccionAuditoria("ENVIAR_RECUPERACION")).toBe("Enviar recuperación de contraseña");
    expect(etiquetaAccionAuditoria("CREAR_SOLICITUD")).toBe("Crear solicitud");
  });

  it("genera una etiqueta legible para acciones futuras", () => {
    expect(etiquetaAccionAuditoria("NUEVA_ACCION")).toBe("Nueva accion");
  });

  it("traduce los nombres técnicos de entidades", () => {
    expect(etiquetaEntidadAuditoria("RegistrationRequest")).toBe("Solicitud de registro");
    expect(etiquetaEntidadAuditoria("ProductiveUnit")).toBe("Unidad Productiva");
  });

  it("normaliza las descripciones históricas", () => {
    expect(etiquetaDescripcionAuditoria("Cambio de estado de productiveunit")).toBe("Cambio de estado de Unidad Productiva");
    expect(etiquetaDescripcionAuditoria("Restaurar de productiveunit")).toBe("Restauración de Unidad Productiva");
    expect(etiquetaDescripcionAuditoria("Crear solicitud de registrationrequest")).toBe("Creación de solicitud de registro");
    expect(etiquetaDescripcionAuditoria("Intento recuperacion fallido de usuario")).toBe("Intento de recuperación fallido de usuario");
    expect(etiquetaDescripcionAuditoria("Enviar recuperacion de usuario")).toBe("Envío de recuperación de contraseña de usuario");
  });
});
