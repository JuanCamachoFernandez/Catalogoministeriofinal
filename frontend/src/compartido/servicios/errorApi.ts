import axios from "axios";

type ApiErrorPayload = { error?: string; details?: Record<string, string[] | string> };

export function errorApi(error: unknown, fallback = "Ocurrió un error inesperado.") {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) return fallback;
  const payload = error.response?.data;
  if (payload?.details) {
    const detail = Object.entries(payload.details)
      .flatMap(([field, value]) => {
        const messages = Array.isArray(value) ? value : [value];
        return messages.map((mensaje) => `${field}: ${mensaje}`);
      })
      .join(" · ");
    if (detail) return detail;
  }
  return payload?.error || fallback;
}


