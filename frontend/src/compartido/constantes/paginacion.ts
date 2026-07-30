import type { Pagination } from "../tipos/contratos";

export const paginacionVacia: Pagination = {
  page: 1,
  per_page: 20,
  pages: 0,
  total: 0,
  has_next: false,
  has_prev: false,
};

