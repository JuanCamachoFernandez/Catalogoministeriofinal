import { expect, test } from "@playwright/test";

const pagination = (total: number) => ({
  page: 1,
  per_page: 9,
  pages: total ? 1 : 0,
  total,
  has_next: false,
  has_prev: false,
});

const fair = {
  id: "feria-1",
  slug: "feria-productiva",
  nombre: "Feria Productiva",
  descripcion: "Oferta nacional",
  lugar: "Plaza Mayor",
  direccion: "Avenida principal",
  departamento: "La Paz",
  municipio: "La Paz",
  fecha_inicio: "2026-07-17",
  fecha_fin: "2026-07-20",
  imagen_portada: null,
  estado: "PUBLISHED",
  visible_publicamente: true,
};

test("informa cuando no existen ferias publicadas", async ({ page }) => {
  await page.route("**/api/public/fairs**", (route) => route.fulfill({
    json: { items: [], pagination: pagination(0) },
  }));
  await page.goto("/catalogo");
  await expect(page.getByRole("heading", { name: "No hay ferias publicadas" })).toBeVisible();
});

test("navega desde las ferias hasta los expositores", async ({ page }) => {
  await page.route("**/api/public/fairs**", (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/feria-productiva")) {
      return route.fulfill({
        json: {
          ...fair,
          expositores: [{
            id: "expo-1",
            nombre_comercial: "Manos Bolivianas",
            descripcion: "Artesanías",
            logo: null,
          }],
        },
      });
    }
    return route.fulfill({ json: { items: [fair], pagination: pagination(1) } });
  });
  await page.goto("/catalogo");
  await expect(page.getByRole("heading", { name: "Feria Productiva" })).toBeVisible();
  await page.getByRole("link", { name: "Entrar a la feria" }).click();
  await expect(page.getByRole("heading", { name: "Manos Bolivianas" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver productos" })).toBeVisible();
});
