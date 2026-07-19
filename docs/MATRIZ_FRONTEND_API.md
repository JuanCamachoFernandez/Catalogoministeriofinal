# Matriz de cobertura frontend/API

Esta matriz usa `docs/API.md` y los controladores Flask como fuente de verdad. “Público” no requiere sesión.

| Dominio | Método y ruta | Rol | Cobertura en frontend |
|---|---|---|---|
| Sesión | `POST /auth/login` | Todos | Inicio de sesión y redirección por rol |
| Sesión | `GET /auth/me` | Todos | Restauración y validación de sesión |
| Sesión | `POST /auth/change-password` | Todos | Cambio obligatorio y voluntario |
| Sesión | `POST /auth/logout` | Todos | Revocación antes de limpiar almacenamiento local |
| Sesión | `POST /auth/forgot-password` | Público | Solicitud de recuperación |
| Sesión | `POST /auth/reset-password` | Público | Restablecimiento mediante token |
| Resumen | `GET /admin/dashboard` | Administradores | Indicadores y actividad reciente |
| Administradores | `GET/POST /admin/users` | Superadmin | Listado, búsqueda y creación |
| Administradores | `GET/PATCH /admin/users/:id` | Superadmin | Datos del listado y edición |
| Administradores | `PATCH /admin/users/:id/status` | Superadmin | Activación e inhabilitación |
| Administradores | `DELETE /admin/users/:id` | Superadmin | Eliminación lógica confirmada |
| Administradores | `POST /admin/users/:id/reset-password` | Superadmin | Restablecimiento administrativo |
| Expositores | `GET/POST /exhibitors` | Administradores | Listado, filtros y creación con tipos |
| Expositores | `GET/PATCH/DELETE /exhibitors/:id` | Administradores | Consulta desde listado, edición y eliminación |
| Expositores | `PATCH /exhibitors/:id/status` | Administradores | Activación e inhabilitación |
| Expositores | `GET /exhibitor-types` | Administradores | Opciones del formulario de alta |
| Perfil | `GET/PATCH /exhibitor/profile` | Expositor | Consulta y edición de la empresa propia |
| Ferias | `GET/POST /fairs` | Administradores | Listado, búsqueda, filtro y creación |
| Ferias | `GET/PATCH /fairs/:id` | Administradores | Datos del listado y edición no terminal |
| Ferias | `PATCH /fairs/:id/status` | Administradores | Finalización o cancelación confirmada |
| Ferias | `GET/POST /fairs/:id/images` | Administradores | Listado y carga de galería |
| Ferias | `DELETE /fair-images/:id` | Administradores | Eliminación de imagen |
| Participación | `GET/POST /fairs/:id/exhibitors` | Administradores | Listado y asignación de expositor |
| Participación | `PATCH /fair-exhibitors/:id` | Administradores | Edición de estado, stand, sector y observaciones |
| Productos | `GET/POST /products` | Administradores | Supervisión, búsqueda, filtro por expositor y alta |
| Productos | `GET/PATCH/DELETE /products/:id` | Administradores | Consulta, edición y eliminación lógica |
| Productos propios | `GET/POST /exhibitor/products` | Expositor | Listado, búsqueda y creación propia |
| Productos propios | `GET/PATCH/DELETE /exhibitor/products/:id` | Expositor | Consulta, edición y eliminación propia |
| Imágenes | `GET/POST /products/:id/images` | Administradores | Consulta indirecta y carga |
| Imágenes | `POST /exhibitor/products/:id/images` | Expositor | Carga propia |
| Imágenes | `PATCH/DELETE /product-images/:id` | Según propiedad | Portada, orden, texto alternativo y eliminación |
| Categorías | `GET /categories` | Gestión | Opciones activas para productos |
| Categorías | `GET /admin/categories` | Administradores | Listado completo |
| Categorías | `GET/PATCH/DELETE /categories/:id` | Administradores | Consulta desde listado, edición y eliminación |
| Categorías | `POST /categories` | Administradores | Creación |
| Categorías | `PATCH /categories/:id/status` | Administradores | Activación e inhabilitación |
| Auditoría | `GET /audit` | Administradores | Historial paginado |
| Catálogo | `GET /public/active-fair` | Público | Portada y expositores de feria activa |
| Catálogo | `GET /public/fairs/:slug/exhibitors/:id` | Público | Tienda, búsqueda, filtros y paginación |
| Catálogo | `POST /public/whatsapp-query` | Público | Consulta con `items` y cantidades |
| Archivos | `POST /uploads` | Gestión | Portadas de feria y logos |

## Decisiones de interfaz

- No existe botón para publicar ferias: `PUBLISHED` se deriva automáticamente de las fechas.
- No se seleccionan productos por feria: se derivan del expositor autorizado.
- Los estados terminales desactivan edición, imágenes y participantes.
- La opción “Administradores” solo se muestra y autoriza para `SUPERADMIN`.
- Las imágenes se resuelven contra el origen de `VITE_DIRECCION_SERVICIO`, incluyendo rutas `/uploads`.
