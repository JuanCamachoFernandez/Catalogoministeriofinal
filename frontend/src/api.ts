import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

export const API_URL = import.meta.env.VITE_DIRECCION_SERVICIO ?? "http://localhost:5000/api";
export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("catalog_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshRequest: Promise<string> | null = null;
type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const isReauthentication = error.config?.url?.includes("/auth/reauthenticate");
    const config = error.config as RetriableConfig | undefined;
    const refreshToken = localStorage.getItem("catalog_refresh_token");
    const isSessionCall = config?.url?.includes("/auth/login") || config?.url?.includes("/auth/refresh");
    if (error.response?.status === 401 && config && !config._retried && !isReauthentication && !isSessionCall && refreshToken) {
      config._retried = true;
      try {
        refreshRequest ??= axios.post<{access_token:string}>(`${API_URL}/auth/refresh`, {}, { headers: { Authorization: `Bearer ${refreshToken}` } }).then(response => response.data.access_token).finally(() => { refreshRequest = null; });
        const accessToken = await refreshRequest;
        // Si la sesión se cerró mientras se renovaba el token, no vuelva a
        // guardar credenciales ni repita la petición con una sesión obsoleta.
        if (localStorage.getItem("catalog_refresh_token") !== refreshToken) {
          return Promise.reject(error);
        }
        localStorage.setItem("catalog_token", accessToken);
        config.headers.Authorization = `Bearer ${accessToken}`;
        return api(config);
      } catch {
        window.dispatchEvent(new Event("catalog:unauthorized"));
      }
    } else if (error.response?.status === 401 && !isReauthentication && localStorage.getItem("catalog_token")) {
      window.dispatchEvent(new Event("catalog:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export type UserRole = "ADMIN" | "PRODUCTIVE_UNIT_RESPONSIBLE" | "SUPERADMIN" | "ADMIN_VICEMINISTERIO" | "EXPOSITOR";
export type UserStatus = "ACTIVE" | "INACTIVE" | "LOCKED" | "BLOCKED";
export type ProductStatus = "AVAILABLE" | "OUT_OF_STOCK" | "INACTIVE" | "DELETED";
export type FairStatus = "DRAFT" | "PUBLISHED" | "DISABLED" | "FINISHED";
export type AssignmentStatus = "PENDING" | "AUTHORIZED" | "REJECTED" | "REVOKED";

export interface SessionUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  foto_perfil?: string | null;
  role: UserRole;
  must_change_password: boolean;
}

export interface AdminUser extends SessionUser {
  apellido_paterno: string | null;
  apellido_materno: string | null;
  numero_documento: string | null;
  phone: string | null;
  status: UserStatus;
  cargo: string | null;
  unidad: string | null;
  observaciones?: string | null;
  created_at: string;
}

export interface Pagination {
  page: number;
  per_page: number;
  pages: number;
  total: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Paged<T> {
  items: T[];
  pagination: Pagination;
}

export type RegistrationStatus = "PENDING" | "APPROVED" | "REJECTED";
export type NotificationStatus = "PENDING" | "SENT" | "FAILED";
export type ProductiveUnitStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";
export type SectorStatus = "ACTIVE" | "INACTIVE";
export type CanonicalProductStatus = "DRAFT" | "AVAILABLE" | "OUT_OF_STOCK" | "RETIRED";

export interface ProductiveSectorLink {
  id: string;
  nombre: string;
  estado: SectorStatus;
  es_otro: boolean;
  detalle_otro?: string | null;
}

export interface ProductiveSector {
  id: string;
  nombre: string;
  descripcion?: string | null;
  estado: SectorStatus;
  es_otro: boolean;
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface RegistrationRequest {
  id: string;
  nombre_comercial: string;
  razon_social: string;
  nit?: string | null;
  registro_seprec?: string | null;
  registro_pro_bolivia?: string | null;
  nombre_representante: string;
  nombres_representante: string;
  apellido_paterno_representante: string;
  apellido_materno_representante: string;
  departamento: string;
  direccion_fisica: string;
  telefono_whatsapp: string;
  correo_electronico: string;
  facebook_url?: string | null;
  instagram_url?: string | null;
  tiktok_url?: string | null;
  resena_comercial: string;
  logo_url?: string | null;
  estado: RegistrationStatus;
  fecha_solicitud: string;
  fecha_revision?: string | null;
  motivo_rechazo?: string | null;
  observaciones?: string | null;
  notification_status?: NotificationStatus | null;
  sectores: ProductiveSectorLink[];
  productos: RegistrationRequestedProduct[];
}

export interface RegistrationRequestedProduct {
  id: string;
  nombre_comercial: string;
  descripcion_tecnica: string;
  precio_referencia: number;
  imagen_url: string;
  orden: number;
}

export interface ProductiveUnit {
  id: string;
  user_id: string;
  registration_request_id: string;
  nombre_comercial: string;
  razon_social: string;
  nit?: string | null;
  registro_seprec?: string | null;
  registro_pro_bolivia?: string | null;
  nombre_representante: string;
  nombres_representante: string;
  apellido_paterno_representante: string;
  apellido_materno_representante: string;
  departamento: string;
  direccion_fisica: string;
  telefono_whatsapp: string;
  correo_electronico: string;
  facebook_url?: string | null;
  instagram_url?: string | null;
  tiktok_url?: string | null;
  resena_comercial: string;
  logo_url?: string | null;
  estado: ProductiveUnitStatus;
  sectores: ProductiveSectorLink[];
  cantidad_productos_publicables?: number;
  productos?: CanonicalProduct[];
}

export interface CanonicalProductImage {
  id: string;
  url_imagen: string;
  texto_alternativo?: string | null;
  orden_visualizacion: number;
  es_principal: boolean;
}

export interface CanonicalProduct {
  id: string;
  productive_unit_id: string;
  nombre_comercial: string;
  descripcion_tecnica: string;
  materia_prima: string;
  dimensiones?: string | null;
  colores_disponibles?: string | null;
  certificaciones?: string | null;
  presentacion_empaque: string;
  precio_referencia: number;
  capacidad_produccion_stock: string;
  estado: CanonicalProductStatus;
  imagenes: CanonicalProductImage[];
  publicable: boolean;
  unidad_productiva?: Pick<ProductiveUnit, "id" | "nombre_comercial" | "telefono_whatsapp">;
}

export interface CanonicalFair {
  id: string;
  nombre: string;
  descripcion?: string | null;
  ubicacion: string;
  departamento?: string;
  municipio?: string;
  fecha_inicio: string;
  fecha_fin: string;
  imagen_portada?: string | null;
  estado: FairStatus;
}

export interface FairParticipation {
  id: string;
  fair_id: string;
  productive_unit_id: string;
  nombre_comercial: string;
  estado: AssignmentStatus | "INACTIVE";
  observaciones?: string | null;
  authorized_at?: string | null;
  revoked_at?: string | null;
}

export interface Category {
  id: string;
  nombre: string;
  slug: string;
  descripcion: string | null;
  estado: boolean;
}

export interface ProductImage {
  id: string;
  url: string;
  alt_text?: string | null;
  is_cover: boolean;
  display_order: number;
}

export interface Product {
  id: string;
  exhibitor_id: string;
  nombre_comercial?: string | null;
  category_id: string;
  categoria?: Pick<Category, "id" | "nombre"> | null;
  nombre: string;
  slug: string;
  descripcion: string;
  materiales_o_ingredientes?: string | null;
  lugar_origen?: string | null;
  presentacion?: string | null;
  informacion_adicional?: string | null;
  precio: number | null;
  estado: ProductStatus;
  destacado: boolean;
  imagenes: ProductImage[];
}

export interface Exhibitor {
  id: string;
  user_id?: string;
  nombre_comercial: string;
  tipo_documento?: "CI" | "NIT" | "OTRO";
  numero_documento?: string;
  nombre_responsable?: string;
  apellido_responsable?: string;
  apellido_paterno_responsable?: string;
  apellido_materno_responsable?: string;
  telefono_whatsapp?: string;
  correo?: string;
  departamento?: string;
  municipio?: string;
  direccion?: string | null;
  descripcion?: string | null;
  descripcion_productos?: string | null;
  nombre_tipo_expositor?: string | null;
  type_ids?: string[];
  tipos_expositor?: string[];
  logo?: string | null;
  estado?: UserStatus;
  numero_stand?: string | null;
  sector?: string | null;
  created_at?: string;
}

export interface Fair {
  id: string;
  nombre: string;
  slug: string;
  descripcion: string | null;
  lugar: string;
  direccion: string | null;
  departamento: string;
  municipio: string;
  fecha_inicio: string;
  fecha_fin: string;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  imagen_portada: string | null;
  observaciones?: string | null;
  estado: FairStatus;
  visible_publicamente: boolean;
  expositores?: Exhibitor[];
}

export interface Assignment {
  id: string;
  fair_id: string;
  exhibitor_id: string;
  nombre_comercial: string;
  estado: AssignmentStatus;
  numero_stand: string | null;
  sector: string | null;
  observaciones: string | null;
  authorized_by: string | null;
  authorized_at: string | null;
}

export interface AuditItem {
  id: string;
  accion: string;
  entidad: string;
  entidad_id?: string | null;
  descripcion: string | null;
  usuario: string;
  created_at: string;
}

type ApiErrorPayload = { error?: string; details?: Record<string, string[] | string> };

export function apiError(error: unknown, fallback = "Ocurrió un error inesperado.") {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) return fallback;
  const payload = error.response?.data;
  if (payload?.details) {
    const detail = Object.entries(payload.details)
      .flatMap(([field, value]) => {
        const messages = Array.isArray(value) ? value : [value];
        return messages.map((message) => `${field}: ${message}`);
      })
      .join(" · ");
    if (detail) return detail;
  }
  return payload?.error || fallback;
}

export function assetUrl(path?: string | null) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  try {
    return new URL(path, new URL(API_URL).origin).toString();
  } catch {
    return path;
  }
}

export async function uploadFile(
  file: File,
  folder: "ferias" | "productos" | "logos" | "perfiles",
  onProgress?: (percent: number) => void,
) {
  const data = new FormData();
  data.append("file", file);
  data.append("folder", folder);
  const response = await api.post<{ url: string }>("/uploads", data, {
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress(Math.min(100, Math.round((event.loaded * 100) / event.total)));
      }
    },
  });
  return response.data.url;
}

export const emptyPagination: Pagination = {
  page: 1,
  per_page: 20,
  pages: 0,
  total: 0,
  has_next: false,
  has_prev: false,
};
