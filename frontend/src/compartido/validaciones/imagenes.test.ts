import { describe, expect, it } from "vitest";
import { validarArchivoImagen } from "./imagenes";

const archivo = (type: string, size: number) => ({ type, size }) as File;

describe("validación de imágenes", () => {
  it("explica claramente cuando la imagen supera el peso permitido", () => {
    const result = validarArchivoImagen(
      archivo("image/jpeg", 12.4 * 1024 * 1024),
      { label: "el logotipo" },
    );

    expect(result).toEqual({
      ok: false,
      title: "La imagen pesa demasiado",
      message:
        "El archivo pesa 12.4 MB y el máximo permitido para el logotipo es 10 MB. Elija una imagen más liviana.",
    });
  });

  it("explica los formatos de imagen compatibles", () => {
    const result = validarArchivoImagen(archivo("image/gif", 1024), {
      label: "la imagen del producto",
    });

    expect(result).toEqual({
      ok: false,
      title: "No se puede usar este archivo",
      message:
        "El archivo seleccionado no es una imagen compatible. Elija una imagen JPG, PNG o WebP para la imagen del producto.",
    });
  });
});
