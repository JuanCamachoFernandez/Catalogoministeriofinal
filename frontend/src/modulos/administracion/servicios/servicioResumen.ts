import { api } from "../../../compartido/servicios/clienteHttp";

export const servicioResumen = {
  get: <T>() => api.get<T>("/admin/dashboard").then(({ data }) => data),
};
