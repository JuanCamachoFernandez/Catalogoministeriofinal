// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  entornoOptimizacionImagen,
  optimizarImagenAntesDeSubir,
  prepararFormularioImagenParaSubida,
} from "./optimizacionImagen";

function crearArchivo(name: string, type: string, size: number) {
  return new File([new Uint8Array(size)], name, { type });
}

function simularEntornoImagen(options?: {
  blobs?: Record<string, Blob | null>;
  hasTransparency?: boolean;
  height?: number;
  width?: number;
}) {
  const width = options?.width ?? 2400;
  const height = options?.height ?? 1800;
  const blobs = options?.blobs ?? {};
  const context = {
    clearRect: vi.fn(),
    drawImage: vi.fn(),
    getImageData: vi.fn(() => ({
      data: new Uint8ClampedArray([255, 255, 255, options?.hasTransparency ? 200 : 255]),
    })),
  } as unknown as CanvasRenderingContext2D;

  vi.spyOn(entornoOptimizacionImagen, "cargarImagenDesdeArchivo").mockResolvedValue({
    naturalWidth: width,
    naturalHeight: height,
    width,
    height,
  } as HTMLImageElement);
  vi.spyOn(entornoOptimizacionImagen, "detectarTransparencia").mockResolvedValue(
    options?.hasTransparency ?? false,
  );
  vi.spyOn(entornoOptimizacionImagen, "crearContextoCanvas").mockReturnValue({
    canvas: {} as HTMLCanvasElement,
    context,
  });
  vi.spyOn(entornoOptimizacionImagen, "blobDesdeCanvas").mockImplementation(
    async (_canvas, type) => blobs[type] ?? null,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("optimización previa de imágenes", () => {
  it("reduce dimensiones y convierte a WebP cuando la imagen excede el máximo", async () => {
    const file = crearArchivo("producto.jpg", "image/jpeg", 220_000);
    simularEntornoImagen({
      width: 2400,
      height: 1800,
      blobs: {
        "image/webp": new Blob([new Uint8Array(120_000)], { type: "image/webp" }),
        "image/jpeg": new Blob([new Uint8Array(150_000)], { type: "image/jpeg" }),
      },
    });

    const result = await optimizarImagenAntesDeSubir(file, "product");

    expect(result.metadata.changed).toBe(true);
    expect(result.metadata.optimizedWidth).toBe(1600);
    expect(result.metadata.optimizedHeight).toBe(1200);
    expect(result.file.type).toBe("image/webp");
    expect(result.file.size).toBe(120_000);
  });

  it("conserva el archivo original cuando el ahorro no es material", async () => {
    const file = crearArchivo("logo.png", "image/png", 100_000);
    simularEntornoImagen({
      width: 800,
      height: 800,
      hasTransparency: true,
      blobs: {
        "image/webp": new Blob([new Uint8Array(97_000)], { type: "image/webp" }),
        "image/png": new Blob([new Uint8Array(99_000)], { type: "image/png" }),
      },
    });

    const result = await optimizarImagenAntesDeSubir(file, "unit_logo");

    expect(result.file).toBe(file);
    expect(result.metadata.changed).toBe(false);
    expect(result.metadata.fallbackReason).toBe(null);
    expect(result.metadata.optimizedWidth).toBe(800);
    expect(result.metadata.optimizedHeight).toBe(800);
  });

  it("preserva la ruta transparente usando formatos compatibles", async () => {
    const file = crearArchivo("logo.png", "image/png", 210_000);
    simularEntornoImagen({
      width: 1800,
      height: 1800,
      hasTransparency: true,
      blobs: {
        "image/webp": new Blob([new Uint8Array(110_000)], { type: "image/webp" }),
        "image/png": new Blob([new Uint8Array(150_000)], { type: "image/png" }),
      },
    });

    const result = await optimizarImagenAntesDeSubir(file, "unit_logo");

    expect(result.metadata.hasTransparency).toBe(true);
    expect(result.metadata.changed).toBe(true);
    expect(result.file.type).toBe("image/webp");
    expect(result.metadata.optimizedWidth).toBe(1000);
    expect(result.metadata.optimizedHeight).toBe(1000);
  });

  it("vuelve al archivo original si la versión procesada supera el límite permitido", async () => {
    const file = crearArchivo("producto.jpg", "image/jpeg", 9 * 1024 * 1024);
    simularEntornoImagen({
      width: 2200,
      height: 1600,
      blobs: {
        "image/webp": new Blob([new Uint8Array(11 * 1024 * 1024)], {
          type: "image/webp",
        }),
      },
    });

    const result = await optimizarImagenAntesDeSubir(file, "product");

    expect(result.file).toBe(file);
    expect(result.metadata.changed).toBe(false);
    expect(result.metadata.fallbackReason).toBe("post_validation_failed");
  });

  it("rechaza tipos no permitidos", async () => {
    const file = crearArchivo("animacion.gif", "image/gif", 12_000);

    await expect(
      optimizarImagenAntesDeSubir(file, "product"),
    ).rejects.toThrow("Formato de imagen no permitido");
  });

  it("hace fallback al original cuando falla la decodificación local", async () => {
    const file = crearArchivo("producto.webp", "image/webp", 80_000);
    vi.spyOn(entornoOptimizacionImagen, "cargarImagenDesdeArchivo").mockRejectedValue(
      new Error("boom"),
    );

    const result = await optimizarImagenAntesDeSubir(file, "product");

    expect(result.file).toBe(file);
    expect(result.metadata.changed).toBe(false);
    expect(result.metadata.fallbackReason).toBe("encode_failed");
  });

  it("agrega el archivo optimizado y campos adicionales al FormData", async () => {
    const file = crearArchivo("producto.jpg", "image/jpeg", 220_000);
    simularEntornoImagen({
      blobs: {
        "image/webp": new Blob([new Uint8Array(120_000)], { type: "image/webp" }),
      },
    });

    const { form, optimization } = await prepararFormularioImagenParaSubida(
      file,
      "product",
      { alt_text: "Imagen del producto" },
    );

    expect(optimization.metadata.changed).toBe(true);
    expect(form.get("alt_text")).toBe("Imagen del producto");
    expect(form.get("file")).toBeInstanceOf(File);
    expect((form.get("file") as File).type).toBe("image/webp");
  });
});
