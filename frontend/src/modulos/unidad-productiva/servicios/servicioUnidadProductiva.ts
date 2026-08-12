import {
  api,
  type Paged,
  type ProductiveSector,
  type ProductiveSectorLink,
  type ProductiveUnit,
} from "../../../compartido";
import { prepararFormularioImagenParaSubida } from "../../../compartido/servicios/optimizacionImagen";

export const servicioUnidadProductiva = {
  getProfile: () =>
    api
      .get<ProductiveUnit>("/productive-unit/profile")
      .then((response) => response.data),

  updateProfile: (profile: Partial<ProductiveUnit>) =>
    api.patch("/productive-unit/profile", profile),

  uploadLogo: async (file: File) => {
    const { form } = await prepararFormularioImagenParaSubida(
      file,
      "unit_logo",
    );
    return api.post("/productive-unit/logo", form);
  },

  getAvailableSectors: () =>
    api
      .get<Paged<ProductiveSector>>("/productive-sectors", {
        params: { per_page: 100 },
      })
      .then((response) => response.data.items),

  getOwnSectors: () =>
    api
      .get<{ sectores: ProductiveSectorLink[] }>("/productive-unit/sectors")
      .then((response) => response.data.sectores),

  updateSectors: (
    sectors: Array<{
      productive_sector_id: string;
      detalle_otro: string | null;
    }>,
  ) => api.put("/productive-unit/sectors", { sectores: sectors }),
};
