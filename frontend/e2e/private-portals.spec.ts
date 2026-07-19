import { expect, test, type Page } from "@playwright/test";

const pagination = { page: 1, per_page: 20, pages: 0, total: 0, has_next: false, has_prev: false };
const users = {
  superadmin: { id: "user-super", username: "superadmin", email: "superadmin@gmail.com", first_name: "Super", last_name: "Admin", role: "SUPERADMIN", must_change_password: false },
  admin: { id: "user-admin", username: "admin", email: "admin@gmail.com", first_name: "Ana", last_name: "Administradora", role: "ADMIN_VICEMINISTERIO", must_change_password: false },
  exhibitor: { id: "user-expo", username: "expositor", email: "expo@gmail.com", first_name: "Eva", last_name: "Expositora", role: "EXPOSITOR", must_change_password: false },
} as const;

async function authenticated(page: Page, user: (typeof users)[keyof typeof users]) {
  await page.addInitScript((sessionUser) => {
    localStorage.setItem("catalog_token", "jwt-de-prueba");
    localStorage.setItem("catalog_user", JSON.stringify(sessionUser));
  }, user);
  await page.route("**/api/auth/me", (route) => route.fulfill({ json: user }));
}

test("el superadministrador puede abrir la gestión de administradores", async ({ page }) => {
  await authenticated(page, users.superadmin);
  await page.route("**/api/admin/dashboard", (route) => route.fulfill({ json: { stats: { feria_activa: null, ferias: 0, ferias_publicadas: 0, expositores_activos: 0, productos: 0, productos_disponibles: 0, productos_sin_stock: 0, asignaciones_pendientes: 0 }, recent_audits: [] } }));
  await page.goto("/gestion/admin/dashboard");
  await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Administradores" })).toBeVisible();
});

test("el administrador normal no ve la gestión de administradores", async ({ page }) => {
  await authenticated(page, users.admin);
  await page.route("**/api/admin/dashboard", (route) => route.fulfill({ json: { stats: { feria_activa: null, ferias: 0, ferias_publicadas: 0, expositores_activos: 0, productos: 0, productos_disponibles: 0, productos_sin_stock: 0, asignaciones_pendientes: 0 }, recent_audits: [] } }));
  await page.goto("/gestion/admin/dashboard");
  await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Administradores" })).toHaveCount(0);
});

test("el expositor administra únicamente su perfil", async ({ page }) => {
  await authenticated(page, users.exhibitor);
  await page.route("**/api/exhibitor/profile", (route) => route.fulfill({ json: { id: "expo-1", nombre_comercial: "Manos Creativas", telefono_whatsapp: "59170000000", departamento: "La Paz", municipio: "La Paz", direccion: "Centro", descripcion: "Artesanías", descripcion_productos: "Textiles", logo: null, estado: "ACTIVE" } }));
  await page.goto("/gestion/expositor/perfil");
  await expect(page.getByRole("heading", { name: "Perfil del expositor" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Administradores" })).toHaveCount(0);
  await expect(page.getByLabel("Nombre comercial")).toHaveValue("Manos Creativas");
});

test("el formulario de acceso redirige según el rol", async ({ page }) => {
  await page.route("**/api/auth/login", (route) => route.fulfill({ json: { access_token: "jwt-login", user: users.superadmin } }));
  await page.route("**/api/admin/dashboard", (route) => route.fulfill({ json: { stats: { feria_activa: null, ferias: 0, ferias_publicadas: 0, expositores_activos: 0, productos: 0, productos_disponibles: 0, productos_sin_stock: 0, asignaciones_pendientes: 0 }, recent_audits: [] } }));
  await page.goto("/gestion/login");
  await page.getByLabel("Usuario o correo electrónico").fill("superadmin");
  await page.getByLabel("Contraseña", { exact: true }).fill("Temporal2026!");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/gestion\/admin\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible();
});
