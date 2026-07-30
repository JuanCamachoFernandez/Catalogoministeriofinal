import { api } from "./clienteHttp";

export async function subirArchivo(
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

