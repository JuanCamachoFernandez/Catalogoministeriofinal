import { describe, expect, it } from "vitest";
import {
  direccionGmail,
  parteLocalGmail,
  nombreVisibleResponsable,
} from "./utilidadesUsuarioAdministracion";

describe("datos de administradores", () => {
  it("muestra solo el usuario de una cuenta Gmail", () => {
    expect(parteLocalGmail("persona@gmail.com")).toBe("persona");
  });

  it("compone siempre una dirección Gmail válida", () => {
    expect(direccionGmail(" persona ")).toBe("persona@gmail.com");
    expect(direccionGmail("persona@otro.com")).toBe("persona@gmail.com");
  });

  it("usa el nombre completo del responsable como nombre comercial", () => {
    expect(nombreVisibleResponsable(" María ", "López", "Quispe")).toBe(
      "María López Quispe",
    );
  });
});
