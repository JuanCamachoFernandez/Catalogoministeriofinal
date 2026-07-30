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

