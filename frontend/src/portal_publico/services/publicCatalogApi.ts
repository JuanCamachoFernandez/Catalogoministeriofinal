import {
  api,
  type CanonicalProduct,
  type Paged,
  type ProductiveSector,
  type ProductiveUnit,
} from "../../api";
import type { ActiveFairsResponse } from "../types";

export const publicCatalogApi = {
  getActiveFairs: ({
    page = 1,
    perPage = 100,
    query = "",
  }: { page?: number; perPage?: number; query?: string } = {}) =>
    api
      .get<ActiveFairsResponse>("/public/fairs/active", {
        params: { page, per_page: perPage, q: query || undefined },
      })
      .then((response) => response.data),

  getSectors: () =>
    api
      .get<Paged<ProductiveSector>>("/productive-sectors", {
        params: { per_page: 100 },
      })
      .then((response) => response.data.items),

  getFairUnits: ({
    fairId,
    query,
    sectorId,
    department,
    page,
  }: {
    fairId: string;
    query: string;
    sectorId: string;
    department: string;
    page: number;
  }) =>
    api
      .get<Paged<ProductiveUnit>>("/public/productive-units", {
        params: {
          fair_id: fairId,
          q: query || undefined,
          sector_id: sectorId || undefined,
          departamento: department || undefined,
          page,
          per_page: 12,
        },
      })
      .then((response) => response.data),

  getFairUnit: (fairId: string, unitId: string) =>
    api
      .get<ProductiveUnit>(`/public/productive-units/${unitId}`, {
        params: { fair_id: fairId },
      })
      .then((response) => response.data),

  getFairUnitProducts: (fairId: string, unitId: string, page: number) =>
    api
      .get<Paged<CanonicalProduct>>("/public/products", {
        params: {
          fair_id: fairId,
          productive_unit_id: unitId,
          page,
          per_page: 6,
        },
      })
      .then((response) => response.data),

  createWhatsAppUrl: (
    fairId: string,
    items: Array<{ product_id: string; quantity: number }>,
  ) =>
    api
      .post<{ url: string }>("/public/whatsapp", {
        fair_id: fairId,
        items,
      })
      .then((response) => response.data.url),
};
