import type { CanonicalFair, Pagination } from "../../../compartido";

export type RespuestaFeriasActivas = {
  active: boolean;
  fair: CanonicalFair | null;
  items: CanonicalFair[];
  pagination: Pagination;
};
