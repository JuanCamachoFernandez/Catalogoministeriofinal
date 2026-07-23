import { describe, expect, it } from "vitest";
import { auditActionLabel, auditDescriptionLabel, auditEntityLabel } from "./auditLabels";

describe("etiquetas de auditoría", () => {
  it("presenta las acciones con espacios y tildes", () => {
    expect(auditActionLabel("RESTABLECER_CONTRASENA")).toBe("Restablecer contraseña");
    expect(auditActionLabel("INTENTO_RECUPERACION_FALLIDO")).toBe("Intento de recuperación fallido");
    expect(auditActionLabel("ENVIAR_RECUPERACION")).toBe("Enviar recuperación de contraseña");
    expect(auditActionLabel("CREAR_SOLICITUD")).toBe("Crear solicitud");
  });

  it("genera una etiqueta legible para acciones futuras", () => {
    expect(auditActionLabel("NUEVA_ACCION")).toBe("Nueva accion");
  });

  it("traduce los nombres técnicos de entidades", () => {
    expect(auditEntityLabel("RegistrationRequest")).toBe("Solicitud de registro");
    expect(auditEntityLabel("ProductiveUnit")).toBe("Unidad Productiva");
  });

  it("normaliza las descripciones históricas", () => {
    expect(auditDescriptionLabel("Cambio de estado de productiveunit")).toBe("Cambio de estado de Unidad Productiva");
    expect(auditDescriptionLabel("Restaurar de productiveunit")).toBe("Restauración de Unidad Productiva");
    expect(auditDescriptionLabel("Crear solicitud de registrationrequest")).toBe("Creación de solicitud de registro");
    expect(auditDescriptionLabel("Intento recuperacion fallido de usuario")).toBe("Intento de recuperación fallido de usuario");
    expect(auditDescriptionLabel("Enviar recuperacion de usuario")).toBe("Envío de recuperación de contraseña de usuario");
  });
});
