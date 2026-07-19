// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  Empty,
  ConfirmButton,
  FeedbackProvider,
  Modal,
  PaginationBar,
  SearchField,
  SearchableSelect,
  StatusBadge,
} from "./ui";

afterEach(cleanup);

describe("componentes comunes", () => {
  it("traduce los estados técnicos", () => {
    render(<StatusBadge value="AUTHORIZED"/>);
    expect(screen.getByText("Autorizado").textContent).toBe("Autorizado");
  });

  it("limpia una búsqueda", async () => {
    const onChange = vi.fn();
    render(<SearchField value="textiles" onChange={onChange}/>);
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
      <FeedbackProvider>
        <ConfirmButton question="¿Eliminar este registro?" onConfirm={onConfirm}>
          Eliminar
        </ConfirmButton>
      </FeedbackProvider>,
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

  it("navega a la siguiente página", async () => {
    const onPage = vi.fn();
    render(<PaginationBar pagination={{ page: 1, per_page: 20, pages: 2, total: 21, has_next: true, has_prev: false }} onPage={onPage}/>);
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });

  it("muestra un estado vacío comprensible", () => {
    render(<Empty title="Sin productos" description="Cambie los filtros."/>);
    expect(screen.getByText("Sin productos").textContent).toBe("Sin productos");
  });

  it("cambia una selección existente sin tener que borrarla", async () => {
    const onChange = vi.fn();
    render(
      <SearchableSelect
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
