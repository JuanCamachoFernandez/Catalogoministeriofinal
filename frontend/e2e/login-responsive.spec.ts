import { expect, test } from "@playwright/test";

const viewports = [
  { name: "escritorio", width: 1440, height: 900, showsAside: true },
  { name: "portátil", width: 1024, height: 600, showsAside: true },
  { name: "tableta", width: 768, height: 1024, showsAside: false },
  { name: "móvil", width: 390, height: 844, showsAside: false },
  { name: "móvil compacto", width: 320, height: 568, showsAside: false },
];

for (const viewport of viewports) {
  test(`el login se adapta a ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/login");

    await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Registrar Unidad Productiva" })).toHaveAttribute(
      "href",
      "/solicitud-registro",
    );

    const aside = page.locator(".auth-aside");
    if (viewport.showsAside) {
      await expect(aside).toBeVisible();
      await expect(aside.getByText("Una vitrina digital para el talento productivo de Bolivia.")).toBeVisible();
    } else {
      await expect(aside).toBeHidden();
    }

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
  });
}
