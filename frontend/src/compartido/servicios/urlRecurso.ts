import { API_URL } from "./clienteHttp";

export function urlRecurso(path?: string | null) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  try {
    return new URL(path, new URL(API_URL).origin).toString();
  } catch {
    return path;
  }
}


