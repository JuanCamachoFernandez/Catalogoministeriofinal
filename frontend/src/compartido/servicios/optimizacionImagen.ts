import {
  LIMITE_IMAGEN_BYTES,
  TIPOS_IMAGEN_PERMITIDOS,
} from "../validaciones/imagenes";

export type VarianteOptimizacionImagen = "product" | "unit_logo";

type ConfiguracionVariante = {
  maxHeight: number;
  maxWidth: number;
  webpQuality: number;
};

export type MetadatosOptimizacionImagen = {
  changed: boolean;
  fallbackReason: "encode_failed" | "post_validation_failed" | null;
  hasTransparency: boolean;
  optimizedBytes: number;
  optimizedHeight: number;
  optimizedType: string;
  optimizedWidth: number;
  originalBytes: number;
  originalHeight: number;
  originalName: string;
  originalType: string;
  originalWidth: number;
  variant: VarianteOptimizacionImagen;
};

export type ResultadoOptimizacionImagen = {
  file: File;
  metadata: MetadatosOptimizacionImagen;
};

type ValorCampoFormulario = Blob | string;

const AHORRO_MINIMO_BYTES = 24 * 1024;
const RELACION_MINIMA_AHORRO = 0.05;
const MIME_JPEG = "image/jpeg";
const MIME_PNG = "image/png";
const MIME_WEBP = "image/webp";
const VARIANTES: Record<VarianteOptimizacionImagen, ConfiguracionVariante> = {
  product: { maxWidth: 1600, maxHeight: 1600, webpQuality: 0.82 },
  unit_logo: { maxWidth: 1000, maxHeight: 1000, webpQuality: 0.86 },
};

type LienzoRender = {
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
};

type ImagenCargada = HTMLImageElement;

function tipoPermitido(tipo: string) {
  return TIPOS_IMAGEN_PERMITIDOS.includes(
    tipo as (typeof TIPOS_IMAGEN_PERMITIDOS)[number],
  );
}

function extensionParaTipo(tipo: string) {
  if (tipo === MIME_PNG) return "png";
  if (tipo === MIME_WEBP) return "webp";
  return "jpg";
}

function nombreParaTipo(nombreOriginal: string, tipo: string) {
  const base = nombreOriginal.replace(/\.[^.]+$/, "") || "imagen";
  return `${base}.${extensionParaTipo(tipo)}`;
}

function ajustarDimensiones(
  width: number,
  height: number,
  maxWidth: number,
  maxHeight: number,
) {
  const scale = Math.min(1, maxWidth / width, maxHeight / height);
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

function ahorroMinimoRequerido(originalBytes: number) {
  return Math.max(
    AHORRO_MINIMO_BYTES,
    Math.round(originalBytes * RELACION_MINIMA_AHORRO),
  );
}

function listaTiposSalida(tipoOriginal: string, hasTransparency: boolean) {
  if (hasTransparency) return [MIME_WEBP, MIME_PNG];
  if (tipoOriginal === MIME_WEBP) return [MIME_WEBP];
  if (tipoOriginal === MIME_PNG) return [MIME_WEBP, MIME_PNG];
  return [MIME_WEBP, MIME_JPEG];
}

async function crearBlobDesdeCanvas(
  canvas: HTMLCanvasElement,
  type: string,
  quality?: number,
) {
  return new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, type, quality);
  });
}

async function cargarImagenDesdeArchivo(file: File) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise<ImagenCargada>((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = () => reject(new Error("No se pudo cargar la imagen"));
      element.src = objectUrl;
    });
    return image;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function crearContextoCanvas(width: number, height: number): LienzoRender {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("No se pudo preparar el lienzo");
  return { canvas, context };
}

async function detectarTransparencia(
  image: ImagenCargada,
  width: number,
  height: number,
) {
  const sample = ajustarDimensiones(width, height, 512, 512);
  const { canvas, context } = crearContextoCanvas(sample.width, sample.height);
  context.clearRect(0, 0, sample.width, sample.height);
  context.drawImage(image, 0, 0, sample.width, sample.height);
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
  for (let index = 3; index < pixels.length; index += 4) {
    if (pixels[index] < 255) return true;
  }
  return false;
}

export const entornoOptimizacionImagen = {
  blobDesdeCanvas: crearBlobDesdeCanvas,
  cargarImagenDesdeArchivo,
  crearContextoCanvas,
  detectarTransparencia,
};

function metadatosOriginales(
  file: File,
  variant: VarianteOptimizacionImagen,
  dimensions?: { width: number; height: number },
  hasTransparency = file.type !== MIME_JPEG,
): Omit<MetadatosOptimizacionImagen, "changed" | "fallbackReason"> {
  const width = dimensions?.width ?? 0;
  const height = dimensions?.height ?? 0;
  return {
    variant,
    originalName: file.name,
    originalType: file.type,
    originalBytes: file.size,
    originalWidth: width,
    originalHeight: height,
    optimizedWidth: width,
    optimizedHeight: height,
    optimizedBytes: file.size,
    optimizedType: file.type,
    hasTransparency,
  };
}

export async function optimizarImagenAntesDeSubir(
  file: File,
  variant: VarianteOptimizacionImagen,
): Promise<ResultadoOptimizacionImagen> {
  if (!tipoPermitido(file.type)) {
    throw new Error("Formato de imagen no permitido");
  }

  try {
    const image = await entornoOptimizacionImagen.cargarImagenDesdeArchivo(file);
    const originalWidth = image.naturalWidth || image.width;
    const originalHeight = image.naturalHeight || image.height;
    const config = VARIANTES[variant];
    const optimizedDimensions = ajustarDimensiones(
      originalWidth,
      originalHeight,
      config.maxWidth,
      config.maxHeight,
    );
    const dimensionsChanged =
      optimizedDimensions.width !== originalWidth ||
      optimizedDimensions.height !== originalHeight;

    const hasTransparency =
      file.type !== MIME_JPEG &&
      (await entornoOptimizacionImagen
        .detectarTransparencia(image, originalWidth, originalHeight)
        .catch(() => true));

    const { canvas, context } = entornoOptimizacionImagen.crearContextoCanvas(
      optimizedDimensions.width,
      optimizedDimensions.height,
    );
    context.clearRect(0, 0, optimizedDimensions.width, optimizedDimensions.height);
    context.drawImage(
      image,
      0,
      0,
      optimizedDimensions.width,
      optimizedDimensions.height,
    );

    const candidates: File[] = [];
    for (const outputType of listaTiposSalida(file.type, hasTransparency)) {
      const blob = await entornoOptimizacionImagen.blobDesdeCanvas(
        canvas,
        outputType,
        outputType === MIME_WEBP ? config.webpQuality : undefined,
      );
      if (!blob || !tipoPermitido(blob.type || outputType)) continue;
      if (outputType === MIME_WEBP && blob.type !== MIME_WEBP) continue;
      candidates.push(
        new File([blob], nombreParaTipo(file.name, blob.type || outputType), {
          type: blob.type || outputType,
        }),
      );
    }

    const originalMetadata = metadatosOriginales(
      file,
      variant,
      { width: originalWidth, height: originalHeight },
      hasTransparency,
    );

    if (!candidates.length) {
      return {
        file,
        metadata: {
          ...originalMetadata,
          changed: false,
          fallbackReason: "encode_failed",
        },
      };
    }

    const bestCandidate = [...candidates].sort((left, right) => {
      if (left.size !== right.size) return left.size - right.size;
      return left.type === MIME_WEBP ? -1 : 1;
    })[0];

    if (bestCandidate.size > LIMITE_IMAGEN_BYTES) {
      return {
        file,
        metadata: {
          ...originalMetadata,
          changed: false,
          fallbackReason: "post_validation_failed",
        },
      };
    }

    const savedBytes = file.size - bestCandidate.size;
    const useOptimizedVersion =
      bestCandidate.size < file.size &&
      (dimensionsChanged || savedBytes >= ahorroMinimoRequerido(file.size));

    if (!useOptimizedVersion) {
      return {
        file,
        metadata: {
          ...originalMetadata,
          changed: false,
          fallbackReason: null,
        },
      };
    }

    return {
      file: bestCandidate,
      metadata: {
        ...originalMetadata,
        optimizedWidth: optimizedDimensions.width,
        optimizedHeight: optimizedDimensions.height,
        optimizedBytes: bestCandidate.size,
        optimizedType: bestCandidate.type,
        changed: true,
        fallbackReason: null,
      },
    };
  } catch {
    return {
      file,
      metadata: {
        ...metadatosOriginales(file, variant),
        changed: false,
        fallbackReason: "encode_failed",
      },
    };
  }
}

export async function prepararFormularioImagenParaSubida(
  file: File,
  variant: VarianteOptimizacionImagen,
  fields?: Record<string, ValorCampoFormulario>,
) {
  const optimization = await optimizarImagenAntesDeSubir(file, variant);
  const form = new FormData();
  form.append("file", optimization.file);
  Object.entries(fields ?? {}).forEach(([name, value]) => {
    form.append(name, value);
  });
  return { form, optimization };
}
