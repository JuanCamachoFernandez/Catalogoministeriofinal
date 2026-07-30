import { api } from "../../../compartido/servicios/clienteHttp";
import type { AuditItem, Paged } from "../../../compartido/tipos/contratos";

export const servicioAuditoria = {
  list: (params: Record<string, string | number | undefined>) =>
    api.get<Paged<AuditItem>>("/admin/audits", { params }).then(({ data }) => data),
  detail: <T>(auditId: string) =>
    api.get<T>(`/admin/audits/${auditId}`).then(({ data }) => data),
};
