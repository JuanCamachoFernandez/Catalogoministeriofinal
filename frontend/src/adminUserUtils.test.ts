import { describe, expect, it } from "vitest";
import {
  gmailAddress,
  gmailLocalPart,
  responsibleDisplayName,
} from "./adminUserUtils";

describe("datos de administradores", () => {
  it("muestra solo el usuario de una cuenta Gmail", () => {
    expect(gmailLocalPart("persona@gmail.com")).toBe("persona");
  });

  it("compone siempre una dirección Gmail válida", () => {
    expect(gmailAddress(" persona ")).toBe("persona@gmail.com");
    expect(gmailAddress("persona@otro.com")).toBe("persona@gmail.com");
  });

  it("usa el nombre completo del responsable como nombre comercial", () => {
    expect(responsibleDisplayName(" María ", "López", "Quispe")).toBe(
      "María López Quispe",
    );
  });
});
