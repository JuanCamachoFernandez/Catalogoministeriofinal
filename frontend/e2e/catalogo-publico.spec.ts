import { expect, test } from "@playwright/test";

const pagination = (total: number) => ({
  page: 1,
  per_page: 20,
  pages: total ? 1 : 0,
  total,
  has_next: false,
  has_prev: false,
});
const fair = {
  id: "feria-1",
  nombre: "Feria Productiva",
  descripcion: "Oferta nacional",
  ubicacion: "Plaza Mayor",
  departamento: "La Paz",
  municipio: "La Paz",
  fecha_inicio: "2026-07-21",
  fecha_fin: "2026-07-24",
  imagen_portada: null,
  estado: "PUBLISHED",
};
const product = {
  id: "producto-1",
  productive_unit_id: "unidad-1",
  nombre_comercial: "Manta andina",
  descripcion_tecnica: "Tejido artesanal",
  materia_prima: "Lana",
  presentacion_empaque: "Unidad",
  precio_referencia: 120,
  capacidad_produccion_stock: "20 unidades",
  estado: "AVAILABLE",
  publicable: true,
  imagenes: [
    {
      id: "img-1",
      url_imagen: "/imagen-1.png",
      texto_alternativo: "Manta frontal",
      orden_visualizacion: 0,
      es_principal: true,
    },
    {
      id: "img-2",
      url_imagen: "/imagen-2.png",
      texto_alternativo: "Manta lateral",
      orden_visualizacion: 1,
      es_principal: false,
    },
    {
      id: "img-3",
      url_imagen: "/imagen-3.png",
      texto_alternativo: "Manta detalle",
      orden_visualizacion: 2,
      es_principal: false,
    },
  ],
};
const unit = {
  id: "unidad-1",
  user_id: "resp-1",
  registration_request_id: "sol-1",
  nombre_comercial: "Manos Bolivianas",
  razon_social: "Manos Bolivianas SRL",
  nombre_representante: "Eva Quispe Mamani",
  nombres_representante: "Eva",
  apellido_paterno_representante: "Quispe",
  apellido_materno_representante: "Mamani",
  departamento: "La Paz",
  direccion_fisica: "Centro",
  telefono_whatsapp: "70000000",
  correo_electronico: "unidad@gmail.com",
  resena_comercial: "Textiles hechos por manos bolivianas.",
  logo_url: null,
  estado: "ACTIVE",
  sectores: [
    { id: "sector-1", nombre: "Textiles", estado: "ACTIVE", es_otro: false },
  ],
  cantidad_productos_publicables: 1,
  productos: [product],
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/productive-sectors**", (route) =>
    route.fulfill({ json: { items: unit.sectores } }),
  );
});

test("informa cuando no existe una feria activa", async ({ page }) => {
  await page.route((url) => url.pathname === "/api/public/fairs/active", (route) =>
    route.fulfill({
      headers: { "access-control-allow-origin": "*" },
      json: { active: false, fair: null, items: [], pagination: pagination(0) },
    }),
  );
  await page.goto("/catalogo");
  await expect(
    page.getByRole("heading", {
      name: "No hay ferias activas en este momento",
    }),
  ).toBeVisible();
});

test("navega de la feria al expositor y sus productos", async ({ page }) => {
  await page.route((url) => url.pathname === "/api/public/fairs/active", (route) =>
    route.fulfill({
      headers: { "access-control-allow-origin": "*" },
      json: { active: true, fair, items: [fair], pagination: pagination(1) },
    }),
  );
  await page.route("**/api/public/productive-units?**", (route) =>
    route.fulfill({
      json: {
        active_catalog: true,
        fair,
        items: [unit],
        pagination: pagination(1),
      },
    }),
  );
  await page.route("**/api/public/productive-units/unidad-1?**", (route) =>
    route.fulfill({ json: unit }),
  );
  await page.route("**/api/public/products?**", (route) =>
    route.fulfill({
      json: { items: [product], pagination: pagination(1) },
    }),
  );
  await page.goto("/catalogo");
  await expect(
    page.getByRole("heading", { name: "Feria Productiva" }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Entrar a la feria/ }).click();
  await expect(
    page.getByRole("heading", { name: "Unidades Productivas participantes" }),
  ).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await page.getByRole("button", { name: "Filtrar por sector" }).click();
  const sectorMenu = page.locator(".searchable-select-menu");
  await expect(sectorMenu).toBeVisible();
  const menuBox = await sectorMenu.boundingBox();
  const viewport = page.viewportSize();
  expect(menuBox).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(menuBox!.x).toBeGreaterThanOrEqual(0);
  expect(menuBox!.x + menuBox!.width).toBeLessThanOrEqual(viewport!.width);
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("heading", { name: "Manos Bolivianas" }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Ver productos/ }).click();
  await expect(
    page.getByRole("heading", { name: "Manos Bolivianas" }),
  ).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await expect(
    page.getByRole("button", { name: "Manta andina", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Manta andina", exact: true }).click();
  await expect(page.getByText("1 de 3")).toBeVisible();
  await page.getByRole("button", { name: "Ver imagen 2" }).click();
  await expect(page.getByText("2 de 3")).toBeVisible();
  await page
    .getByRole("button", { name: "Ampliar imagen del producto" })
    .click();
  await expect(page.locator(".product-lightbox")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".product-lightbox")).not.toBeVisible();
  const productDetail = page.locator(".product-detail-dialog");
  await productDetail
    .getByRole("button", { name: "Agregar Manta andina" })
    .click();
  await productDetail
    .getByRole("button", { name: "Agregar Manta andina" })
    .click();
  await expect(
    productDetail.getByText("2 unidades seleccionadas"),
  ).toBeVisible();
  await expect(productDetail.getByText("Bs 240.00")).toBeVisible();
  await productDetail
    .getByRole("button", { name: "Guardar selección" })
    .click();
  await expect(
    page.getByRole("button", { name: /Consultar por WhatsApp/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /2 unidades/ }).click();
  await expect(
    page.getByRole("heading", { name: "Resumen de la consulta" }),
  ).toBeVisible();
  await expect(page.getByText("Total referencial")).toBeVisible();
});
