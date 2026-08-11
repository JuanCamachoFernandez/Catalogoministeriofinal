const IMAGE_MAX_BYTES = 10 * 1024 * 1024;
const IMAGE_ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"] as const;

type ImageValidationOptions = {
  label: string;
};

type ImageValidationResult =
  | { ok: true }
  | { ok: false; title: string; message: string };

export function validarArchivoImagen(
  file: File,
  options: ImageValidationOptions,
): ImageValidationResult {
  if (!IMAGE_ALLOWED_TYPES.includes(file.type as (typeof IMAGE_ALLOWED_TYPES)[number])) {
    return {
      ok: false,
      title: "Formato no permitido",
      message: `Seleccione una imagen JPG, PNG o WebP para ${options.label}.`,
    };
  }
  if (file.size > IMAGE_MAX_BYTES) {
    return {
      ok: false,
      title: "Imagen demasiado grande",
      message: `${options.label} no puede superar los 10 MB.`,
    };
  }
  return { ok: true };
}

export const LIMITE_IMAGEN_MB = 10;
