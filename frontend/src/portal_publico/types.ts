import type { CanonicalFair, Pagination } from "../api";

export type ActiveFairsResponse = {
  active: boolean;
  fair: CanonicalFair | null;
  items: CanonicalFair[];
  pagination: Pagination;
};
