import { apiError, emptyPagination, type Paged } from "../api";

export const pageData = <T,>(value?: Paged<T>) =>
  value ?? { items: [], pagination: emptyPagination };

export const message = (error: unknown) =>
  apiError(error, "No se pudo completar la operación.");

export const clean = (value: string) => value.trim() || null;
