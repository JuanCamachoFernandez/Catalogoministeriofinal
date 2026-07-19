import path from "node:path";
import { expect, test } from "@playwright/test";

const captures = path.resolve(process.cwd(), "../docs/capturas");

test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-desktop", "Las capturas se generan una sola vez en Chromium de escritorio.");
});

test("genera la captura del catálogo público", async ({ page }) => {
  await page.route("**/api/public/fairs**", (route) => route.fulfill({ json: { items: [{ id: "feria-1", slug: "feria-productiva", nombre: "Feria Productiva Boliviana", descripcion: "Descubra productos elaborados por emprendimientos de todo el país.", lugar: "Campo Ferial", departamento: "La Paz", municipio: "La Paz", fecha_inicio: "2026-07-17", fecha_fin: "2026-07-20", imagen_portada: null, estado: "PUBLISHED", visible_publicamente: true }], pagination: { page: 1, per_page: 9, pages: 1, total: 1, has_next: false, has_prev: false } } }));
  await page.goto("/catalogo");
  await expect(page.getByRole("heading", { name: "Feria Productiva Boliviana" })).toBeVisible();
  await page.screenshot({ path: path.join(captures, "catalogo-publico.png"), fullPage: true });
});

test("genera la captura del panel administrativo", async ({ page }) => {
  const user = { id: "user-super", username: "superadmin", email: "superadmin@gmail.com", first_name: "Super", last_name: "Admin", role: "SUPERADMIN", must_change_password: false };
  await page.addInitScript((sessionUser) => { localStorage.setItem("catalog_token", "jwt-captura"); localStorage.setItem("catalog_user", JSON.stringify(sessionUser)); }, user);
  await page.route("**/api/auth/me", (route) => route.fulfill({ json: user }));
  await page.route("**/api/admin/dashboard", (route) => route.fulfill({ json: { stats: { feria_activa: "Feria Productiva Boliviana", ferias: 8, ferias_publicadas: 1, expositores_activos: 42, productos: 186, productos_disponibles: 154, productos_sin_stock: 21, asignaciones_pendientes: 6 }, recent_audits: [{ id: "audit-1", accion: "AUTORIZAR", entidad: "FeriaExpositor", descripcion: "Expositor autorizado para la feria", created_at: "2026-07-17T14:30:00Z" }, { id: "audit-2", accion: "EDITAR", entidad: "Producto", descripcion: "Producto actualizado por expositor", created_at: "2026-07-17T13:10:00Z" }] } }));
  await page.goto("/gestion/admin/dashboard");
  await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible();
  await page.screenshot({ path: path.join(captures, "panel-administrativo.png"), fullPage: true });
});
