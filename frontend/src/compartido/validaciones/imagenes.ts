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
      title: "No se puede usar este archivo",
      message: `El archivo seleccionado no es una imagen compatible. Elija una imagen JPG, PNG o WebP para ${options.label}.`,
    };
  }
  if (file.size > IMAGE_MAX_BYTES) {
    const fileSizeMb = (file.size / (1024 * 1024)).toFixed(1);
    return {
      ok: false,
      title: "La imagen pesa demasiado",
      message: `El archivo pesa ${fileSizeMb} MB y el máximo permitido para ${options.label} es 10 MB. Elija una imagen más liviana.`,
    };
  }
  return { ok: true };
}

export const LIMITE_IMAGEN_MB = 10;
