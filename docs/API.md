# API REST

Base local: `http://localhost:5000/api`. Las rutas privadas requieren JWT y respetan los roles `SUPERADMIN`, `ADMIN_VICEMINISTERIO` y `EXPOSITOR`.

## Autenticación

| Método | Ruta | Uso |
|---|---|---|
| POST | `/auth/login` | Iniciar sesión |
| GET | `/auth/me` | Consultar sesión |
| POST | `/auth/change-password` | Cambiar contraseña |
| POST | `/auth/logout` | Revocar token actual |
| POST | `/auth/forgot-password` | Solicitar recuperación |
| POST | `/auth/reset-password` | Confirmar recuperación |

## Administración y empresas

| Método | Ruta | Uso |
|---|---|---|
| GET | `/admin/dashboard` | Indicadores y actividad reciente |
| GET/POST | `/admin/users` | Listar y crear administradores |
| GET/PATCH | `/admin/users/:id` | Consultar y editar administrador |
| PATCH | `/admin/users/:id/status` | Cambiar estado |
| POST | `/admin/users/:id/reset-password` | Restablecimiento administrativo |
| GET/POST | `/exhibitors` | Listar y crear expositores |
| GET/PATCH/DELETE | `/exhibitors/:id` | Consultar, editar o eliminar lógicamente |
| PATCH | `/exhibitors/:id/status` | Cambiar estado de cuenta y expositor |
| GET/PATCH | `/exhibitor/profile` | Perfil del expositor autenticado |
| GET | `/audit` | Auditoría |

## Ferias

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/fairs` | Listar y crear ferias |
| GET/PATCH | `/fairs/:id` | Consultar y editar una feria no terminal |
| PATCH | `/fairs/:id/status` | Finalizar o cancelar definitivamente |
| GET/POST | `/fairs/:id/images` | Galería de una feria |
| DELETE | `/fair-images/:id` | Eliminar imagen de galería |
| GET/POST | `/fairs/:id/exhibitors` | Listar y asignar expositores |
| PATCH | `/fair-exhibitors/:id` | Autorizar, revocar o editar participación |

Las ferias se publican automáticamente según `fecha_inicio` y `fecha_fin`. No se acepta activación manual ni reactivación de estados terminales. Los rangos no pueden superponerse.

## Productos y categorías

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/products` | Productos bajo administración |
| GET/PATCH/DELETE | `/products/:id` | Consultar, editar o eliminar producto |
| GET/POST | `/exhibitor/products` | Productos propios |
| GET/PATCH/DELETE | `/exhibitor/products/:id` | Producto propio |
| GET/POST | `/products/:id/images` | Imágenes de producto |
| POST | `/exhibitor/products/:id/images` | Agregar imagen propia |
| PATCH/DELETE | `/product-images/:id` | Portada, orden, texto y eliminación |
| GET | `/admin/categories` | Todas las categorías |
| GET/POST | `/categories` | Categorías activas o nueva categoría |
| GET/PATCH/DELETE | `/categories/:id` | Consultar, editar o eliminar categoría |
| PATCH | `/categories/:id/status` | Habilitar o inhabilitar categoría |

## Catálogo público

| Método | Ruta | Uso |
|---|---|---|
| GET | `/public/fairs` | Ferias visibles |
| GET | `/public/active-fair` | Feria determinada por fechas |
| GET | `/public/fairs/:slug` | Feria y expositores autorizados |
| GET | `/public/fairs/:slug/exhibitors/:id` | Productos derivados del expositor |
| POST | `/public/whatsapp-query` | Enlace seguro de WhatsApp |

WhatsApp recibe:

```json
{
  "fair_slug": "feria-activa",
  "items": [
    {"product_id": "uuid", "quantity": 2}
  ]
}
```

El backend deriva el teléfono, exige productos disponibles de un solo expositor y valida su autorización en la feria activa.

## Archivos y comandos

- `POST /uploads` recibe `multipart/form-data` con `folder` y `file`.
- `flask sync-fairs` actualiza estados y limpia imágenes huérfanas.
- Las imágenes de feria deben ser archivos locales bajo `/uploads/ferias`.

Los errores mantienen el formato `{"error": "mensaje"}`. La colección completa se encuentra en `postman/`.
