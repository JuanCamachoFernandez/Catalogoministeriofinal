// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../compartido";
import { PaginaRegistro } from "./paginas/PaginaRegistro";

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  vi.spyOn(api, "get").mockResolvedValue({
    data: { items: [], pagination: {} },
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("validación de la solicitud pública", () => {
  it("muestra un pop-up, marca el primer campo inválido y devuelve el foco al cerrarlo", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <PaginaRegistro/>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Enviar solicitud" }));

    const nameInput = document.querySelector<HTMLInputElement>('input[name="nombre_comercial"]');
    expect(nameInput).not.toBeNull();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(nameInput?.getAttribute("aria-invalid")).toBe("true");
    expect(document.activeElement).toBe(nameInput);

    await userEvent.click(screen.getByRole("button", { name: "Cerrar notificación" }));
    await waitFor(() => expect(document.activeElement).toBe(nameInput));

    await userEvent.type(nameInput!, "Manos Andinas");
    expect(nameInput?.hasAttribute("aria-invalid")).toBe(false);
  });
});
