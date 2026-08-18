import { errorApi, paginacionVacia, type Paged } from "../../../compartido";

export const AUDITORIA_HABILITADA = false;

export const datosPagina = <T,>(value?: Paged<T>) =>
  value ?? { items: [], pagination: paginacionVacia };

export const mensaje = (error: unknown) =>
  errorApi(error, "No se pudo completar la operación.");

export const limpiar = (value: string) => value.trim() || null;
