import { api } from "../../../compartido/servicios/clienteHttp";
import { prepararFormularioImagenParaSubida } from "../../../compartido/servicios/optimizacionImagen";
import type {
  CanonicalProduct,
  Paged,
} from "../../../compartido/tipos/contratos";

const baseFor = (admin = false) =>
  admin ? "/admin/products" : "/productive-unit/products";

export const servicioProductos = {
  list: (page: number, perPage: number, admin = false) =>
    api
      .get<Paged<CanonicalProduct>>(baseFor(admin), {
        params: { page, per_page: perPage },
      })
      .then(({ data }) => data),
  create: (payload: unknown) => api.post(baseFor(), payload),
  update: (productId: string, payload: unknown) =>
    api.patch(`${baseFor()}/${productId}`, payload),
  updateStatus: (productId: string, estado: string, admin = false) =>
    api
      .patch<CanonicalProduct>(`${baseFor(admin)}/${productId}/status`, { estado })
      .then(({ data }) => data),
  remove: (productId: string) => api.delete(`${baseFor()}/${productId}`),
  setMainImage: (productId: string, imageId: string) =>
    api.patch(`${baseFor()}/${productId}/images/${imageId}/main`),
  removeImage: (productId: string, imageId: string) =>
    api.delete(`${baseFor()}/${productId}/images/${imageId}`),
  uploadImage: async (
    productId: string,
    file: File,
    fields?: Record<string, string>,
  ) => {
    const { form } = await prepararFormularioImagenParaSubida(
      file,
      "product",
      fields,
    );
    return api.post(`${baseFor()}/${productId}/images`, form);
  },
};
