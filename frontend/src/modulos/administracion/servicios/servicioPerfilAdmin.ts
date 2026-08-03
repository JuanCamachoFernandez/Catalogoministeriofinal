import { api, type AdminUser } from "../../../compartido";

type ActualizacionPerfilAdmin = {
  first_name: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  email: string;
  phone: string | null;
  cargo: string | null;
  unidad: string | null;
  observaciones: string | null;
};

export const servicioPerfilAdmin = {
  get: () => api.get<AdminUser>("/admin/profile").then(({ data }) => data),
  update: (payload: ActualizacionPerfilAdmin) =>
    api.patch<AdminUser>("/admin/profile", payload).then(({ data }) => data),
};
