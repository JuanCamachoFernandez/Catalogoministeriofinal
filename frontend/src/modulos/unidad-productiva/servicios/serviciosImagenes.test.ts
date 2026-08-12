// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../compartido/servicios/clienteHttp";
import * as optimizacionImagen from "../../../compartido/servicios/optimizacionImagen";
import { servicioRegistro } from "../../registro/servicios/servicioRegistro";
import { servicioProductos } from "./servicioProductos";
import { servicioUnidadProductiva } from "./servicioUnidadProductiva";

function crearArchivo(name: string, type = "image/jpeg") {
  return new File([new Uint8Array(1024)], name, { type });
}

function prepararMockSubida() {
  const form = new FormData();
  form.append("file", crearArchivo("optimizada.webp", "image/webp"));
  vi.spyOn(optimizacionImagen, "prepararFormularioImagenParaSubida").mockResolvedValue({
    form,
    optimization: {
      file: form.get("file") as File,
      metadata: {
        changed: true,
        fallbackReason: null,
        hasTransparency: false,
        optimizedBytes: 1024,
        optimizedHeight: 600,
        optimizedType: "image/webp",
        optimizedWidth: 800,
        originalBytes: 2048,
        originalHeight: 1200,
        originalName: "original.jpg",
        originalType: "image/jpeg",
        originalWidth: 1600,
        variant: "product" as const,
      },
    },
  });
  return form;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("servicios de subida con optimización previa", () => {
  it("optimiza el logotipo del registro antes de enviarlo", async () => {
    const file = crearArchivo("logo.jpg");
    const form = prepararMockSubida();
    const post = vi.spyOn(api, "post").mockResolvedValue({
      data: { url: "/uploads/solicitudes/logo.webp" },
    });

    const result = await servicioRegistro.uploadLogo(file);

    expect(optimizacionImagen.prepararFormularioImagenParaSubida).toHaveBeenCalledWith(
      file,
      "unit_logo",
    );
    expect(post).toHaveBeenCalledWith("/registration-requests/logo", form);
    expect(result).toBe("/uploads/solicitudes/logo.webp");
  });

  it("optimiza la imagen de producto del registro antes de enviarla", async () => {
    const file = crearArchivo("producto.jpg");
    const form = prepararMockSubida();
    const post = vi.spyOn(api, "post").mockResolvedValue({
      data: { url: "/uploads/solicitudes/producto.webp" },
    });

    const result = await servicioRegistro.uploadProductImage(file);

    expect(optimizacionImagen.prepararFormularioImagenParaSubida).toHaveBeenCalledWith(
      file,
      "product",
    );
    expect(post).toHaveBeenCalledWith(
      "/registration-requests/products/image",
      form,
    );
    expect(result).toBe("/uploads/solicitudes/producto.webp");
  });

  it("optimiza el logotipo de la unidad productiva antes de enviarlo", async () => {
    const file = crearArchivo("unidad.jpg");
    const form = prepararMockSubida();
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: {} });

    await servicioUnidadProductiva.uploadLogo(file);

    expect(optimizacionImagen.prepararFormularioImagenParaSubida).toHaveBeenCalledWith(
      file,
      "unit_logo",
    );
    expect(post).toHaveBeenCalledWith("/productive-unit/logo", form);
  });

  it("optimiza la imagen de producto y conserva los campos extra del formulario", async () => {
    const file = crearArchivo("producto.jpg");
    const form = prepararMockSubida();
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: {} });

    await servicioProductos.uploadImage("prod-1", file, {
      alt_text: "Imagen de prueba",
    });

    expect(optimizacionImagen.prepararFormularioImagenParaSubida).toHaveBeenCalledWith(
      file,
      "product",
      { alt_text: "Imagen de prueba" },
    );
    expect(post).toHaveBeenCalledWith(
      "/productive-unit/products/prod-1/images",
      form,
    );
  });
});
