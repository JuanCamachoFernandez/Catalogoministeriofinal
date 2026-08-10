// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  EstadoVacio,
  BotonConfirmacion,
  ProveedorRetroalimentacion,
  Modal,
  BarraPaginacion,
  CampoBusqueda,
  SelectorBuscable,
  InsigniaEstado,
  useElementosPaginacionAdaptable,
} from "../../compartido/componentes";
import type { Pagination } from "../../compartido";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("componentes comunes", () => {
  it("traduce los estados técnicos", () => {
    render(<InsigniaEstado value="AUTHORIZED"/>);
    expect(screen.getByText("Autorizado").textContent).toBe("Autorizado");
  });

  it("limpia una búsqueda", async () => {
    const onChange = vi.fn();
    render(<CampoBusqueda value="textiles" onChange={onChange}/>);
    await userEvent.click(screen.getByRole("button", { name: "Limpiar búsqueda" }));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("cierra un modal con Escape", () => {
    const onClose = vi.fn();
    render(<Modal title="Editar producto" onClose={onClose}><p>Formulario</p></Modal>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("muestra el modal sobre la navegación sin quedar limitado por su contenedor", () => {
    const { unmount } = render(
      <div data-testid="contenedor-del-panel">
        <Modal title="Nuevo expositor" onClose={() => undefined}>
          <p>Formulario</p>
        </Modal>
      </div>,
    );
    const backdrop = screen.getByRole("dialog").parentElement;
    expect(backdrop?.parentElement).toBe(document.body);
    expect(document.body.classList.contains("modal-open")).toBe(true);
    unmount();
    expect(document.body.classList.contains("modal-open")).toBe(false);
  });

  it("confirma acciones con un modal central", async () => {
    const onConfirm = vi.fn();
    render(
      <ProveedorRetroalimentacion>
        <BotonConfirmacion question="¿Eliminar este registro?" onConfirm={onConfirm}>
          Eliminar
        </BotonConfirmacion>
      </ProveedorRetroalimentacion>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("¿Eliminar este registro?")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Sí, continuar" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("mantiene el foco dentro del modal", () => {
    render(
      <Modal title="Confirmación" onClose={() => undefined}>
        <button>Primero</button>
        <button>Último</button>
      </Modal>,
    );
    const first = screen.getByRole("button", { name: "Cerrar" });
    const last = screen.getByRole("button", { name: "Último" });
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("conserva el foco al escribir aunque cambie la función de cierre", async () => {
    function FormInModal() {
      const [value, setValue] = useState("");
      return <Modal title="Nueva feria" onClose={() => setValue("")}><input aria-label="Nombre de la feria" value={value} onChange={(event) => setValue(event.target.value)} /></Modal>;
    }
    render(<FormInModal />);
    const input = screen.getByRole("textbox", { name: "Nombre de la feria" });
    await userEvent.type(input, "Feria nacional");
    expect((input as HTMLInputElement).value).toBe("Feria nacional");
    expect(document.activeElement).toBe(input);
  });

  it("navega a la siguiente página", async () => {
    const onPage = vi.fn();
    render(<BarraPaginacion pagination={{ page: 1, per_page: 20, pages: 2, total: 21, has_next: true, has_prev: false }} onPage={onPage}/>);
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });

  it("no mueve el scroll cuando la paginación desactiva el auto-scroll", async () => {
    const onPage = vi.fn();
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    render(
      <BarraPaginacion
        pagination={{ page: 1, per_page: 20, pages: 2, total: 21, has_next: true, has_prev: false }}
        onPage={onPage}
        scrollOnDesktop={false}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(onPage).toHaveBeenCalledWith(2);
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("puede mantener la paginación completa en móvil sin mostrar ver más", () => {
    render(
      <BarraPaginacion
        pagination={{ page: 2, per_page: 5, pages: 4, total: 20, has_next: true, has_prev: true }}
        mobileCompact={false}
      />,
    );
    expect(screen.getByLabelText("Páginas disponibles")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Ver más resultados" })).toBeNull();
  });

  it("conserva los elementos anteriores al cargar más en móvil", async () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })));
    const MobileList = ({ items, pagination }: {
      items: { id: string; name: string }[];
      pagination: Pagination;
    }) => {
      const displayed = useElementosPaginacionAdaptable(items, pagination, "ferias");
      return <div>{displayed.map((item) => <span key={item.id}>{item.name}</span>)}</div>;
    };
    const firstPage = Array.from({ length: 6 }, (_, index) => ({
      id: String(index + 1), name: `Demo ${index + 1}`,
    }));
    const secondPage = Array.from({ length: 6 }, (_, index) => ({
      id: String(index + 7), name: `Demo ${index + 7}`,
    }));
    const { rerender } = render(<MobileList items={firstPage} pagination={{
      page: 1, per_page: 6, pages: 2, total: 12, has_next: true, has_prev: false,
    }} />);

    rerender(<MobileList items={[]} pagination={{
      page: 1, per_page: 20, pages: 0, total: 0, has_next: false, has_prev: false,
    }} />);
    expect(screen.getByText("Demo 1")).toBeTruthy();

    rerender(<MobileList items={secondPage} pagination={{
      page: 2, per_page: 6, pages: 2, total: 12, has_next: false, has_prev: true,
    }} />);
    await waitFor(() => expect(screen.getByText("Demo 12")).toBeTruthy());
    expect(screen.getByText("Demo 1")).toBeTruthy();
  });

  it("muestra un estado vacío comprensible", () => {
    render(<EstadoVacio title="Sin productos" description="Cambie los filtros."/>);
    expect(screen.getByText("Sin productos").textContent).toBe("Sin productos");
  });

  it("cambia una selección existente sin tener que borrarla", async () => {
    const onChange = vi.fn();
    render(
      <SelectorBuscable
        value="Cochabamba"
        ariaLabel="Departamento"
        options={[
          { value: "La Paz", label: "La Paz" },
          { value: "Cochabamba", label: "Cochabamba" },
        ]}
        onChange={onChange}
      />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Departamento" }),
    );
    await userEvent.type(screen.getByPlaceholderText("Buscar…"), "La");
    await userEvent.click(screen.getByRole("button", { name: "La Paz" }));
    expect(onChange).toHaveBeenCalledWith("La Paz");
  });
});
