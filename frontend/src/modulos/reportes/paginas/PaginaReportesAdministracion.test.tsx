// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../compartido";
import { ProveedorRetroalimentacion } from "../../../compartido/componentes";
import PaginaReportesAdministracion from "./PaginaReportesAdministracion";

const reportOptions = {
  resources: [],
  actions: ["CREAR", "EDITAR"],
  sectors: [
    { value: "sector-1", label: "Textiles" },
    { value: "sector-2", label: "Alimentos" },
  ],
  productive_units: [
    { value: "unit-1", label: "Manos Andinas" },
    { value: "unit-2", label: "Sabores del Valle" },
  ],
  fair_locations: [
    { value: "Campo Ferial Chuquiago Marka", label: "Campo Ferial Chuquiago Marka" },
    { value: "Parque Urbano Central", label: "Parque Urbano Central" },
  ],
  departments: ["La Paz", "Cochabamba"],
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderPage() {
  vi.spyOn(api, "get").mockResolvedValue({ data: reportOptions });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ProveedorRetroalimentacion>
        <PaginaReportesAdministracion />
      </ProveedorRetroalimentacion>
    </QueryClientProvider>,
  );
}

async function selectReport(name: string) {
  await userEvent.click(
    screen.getByRole("button", { name: "Seleccionar contenido del reporte" }),
  );
  await userEvent.click(screen.getByRole("button", { name }));
}

describe("filtros de reportes", () => {
  it("presenta multiseleccion y valida el rango de precios sin campos de busqueda", async () => {
    renderPage();
    expect(
      await screen.findByRole("heading", { name: "Reportes" }),
    ).toBeTruthy();

    await selectReport("Productos");
    expect(
      screen.queryByPlaceholderText(
        "Nombre del producto o de la unidad productiva",
      ),
    ).toBeNull();

    await userEvent.click(
      screen.getByRole("button", { name: "Seleccionar unidades productivas" }),
    );
    await userEvent.click(
      screen.getByRole("option", { name: "Manos Andinas" }),
    );
    expect(
      screen.getByRole("button", { name: "Seleccionar unidades productivas" })
        .textContent,
    ).toContain("Manos Andinas");

    await userEvent.type(screen.getByLabelText("Precio mínimo (Bs)"), "100");
    await userEvent.type(screen.getByLabelText("Precio máximo (Bs)"), "10");
    expect(screen.getByRole("alert").textContent).toContain(
      "El precio máximo debe ser igual o mayor que el precio mínimo",
    );
    expect(
      screen
        .getByRole("button", { name: /Generar y descargar/ })
        .hasAttribute("disabled"),
    ).toBe(true);

    await selectReport("Solicitudes de registro");
    expect(
      screen.getByRole("button", { name: "Seleccionar sectores productivos" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Seleccionar departamentos" }),
    ).toBeTruthy();

    await selectReport("Auditoría");
    expect(
      screen.getByRole("button", { name: "Seleccionar acciones" }),
    ).toBeTruthy();

    await selectReport("Ferias y eventos");
    await userEvent.click(
      screen.getByRole("button", { name: "Filtrar por lugar registrado" }),
    );
    expect(
      screen.getByRole("button", { name: "Campo Ferial Chuquiago Marka" }),
    ).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: "Campo Ferial Chuquiago Marka" }),
    );

    await userEvent.type(screen.getByLabelText("Desde"), "2026-08-20");
    await userEvent.type(screen.getByLabelText("Hasta"), "2026-08-20");
    expect(screen.getByRole("alert").textContent).toContain(
      "La fecha final debe ser posterior a la fecha inicial",
    );
    expect(
      screen
        .getByRole("button", { name: /Generar y descargar/ })
        .hasAttribute("disabled"),
    ).toBe(true);

    expect(screen.queryByText("Búsqueda general")).toBeNull();
  });
});

