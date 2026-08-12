import { api } from "../../../compartido/servicios/clienteHttp";
import { prepararFormularioImagenParaSubida } from "../../../compartido/servicios/optimizacionImagen";
import type {
  Paged,
  ProductiveSector,
  RegistrationRequest,
} from "../../../compartido/tipos/contratos";

export const servicioRegistro = {
  listSectors: () =>
    api
      .get<Paged<ProductiveSector>>("/productive-sectors", {
        params: { per_page: 100 },
      })
      .then(({ data }) => data.items),
  uploadLogo: async (file: File) => {
    const { form } = await prepararFormularioImagenParaSubida(
      file,
      "unit_logo",
    );
    return api
      .post<{ url: string }>("/registration-requests/logo", form)
      .then(({ data }) => data.url);
  },
  uploadProductImage: async (file: File) => {
    const { form } = await prepararFormularioImagenParaSubida(file, "product");
    return api
      .post<{ url: string }>("/registration-requests/products/image", form)
      .then(({ data }) => data.url);
  },
  submit: (payload: unknown) =>
    api
      .post<RegistrationRequest>("/registration-requests", payload)
      .then(({ data }) => data),
};
