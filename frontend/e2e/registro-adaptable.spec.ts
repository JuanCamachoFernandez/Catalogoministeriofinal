import { expect, test } from "@playwright/test";

const sectors = [
  { id: "sector-1", nombre: "Textiles", estado: "ACTIVE", es_otro: false },
  { id: "sector-2", nombre: "Alimentos", estado: "ACTIVE", es_otro: false },
  { id: "sector-3", nombre: "Otros", estado: "ACTIVE", es_otro: true },
];

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "tableta", width: 768, height: 1024 },
  { name: "móvil", width: 390, height: 844 },
  { name: "móvil compacto", width: 320, height: 568 },
];

for (const viewport of viewports) {
  test(`el registro se adapta a ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.route("**/api/productive-sectors**", (route) =>
      route.fulfill({ json: { items: sectors, pagination: {} } }),
    );
    await page.goto("/solicitud-registro");

    await expect(page.getByRole("heading", { name: "Solicitud de Unidad Productiva" })).toBeVisible();
    await expect(page.getByLabel("Nombre comercial")).toBeVisible();
    await expect(page.getByLabel("Nombres del representante")).toBeVisible();
    await expect(page.getByLabel("Apellido paterno")).toBeVisible();
    await expect(page.getByLabel("Apellido materno")).toBeVisible();
    await expect(page.getByRole("button", { name: "Enviar solicitud" })).toBeEnabled();
    await page.getByLabel("Textiles").check();
    await expect(page.getByRole("button", { name: "Enviar solicitud" })).toBeEnabled();

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
  });
}
