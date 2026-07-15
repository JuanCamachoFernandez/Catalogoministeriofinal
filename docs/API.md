# API REST

Base local: `http://localhost:5000/api`. Las rutas administrativas requieren JWT y rol autorizado.

## Autenticación

| Método | Ruta | Uso |
|---|---|---|
| POST | `/auth/login` | Iniciar sesión |
| GET | `/auth/me` | Verificar sesión |
| POST | `/auth/change-password` | Cambiar contraseña temporal o actual |

## Administración

| Método | Ruta | Uso |
|---|---|---|
| GET | `/admin/dashboard` | Indicadores reales |
| GET/POST | `/admin/users` | Listar/crear administradores |
| PATCH | `/admin/users/:id/status` | Cambiar estado |
| GET/POST | `/exhibitors` | Listar/crear expositores |
| PATCH | `/exhibitors/:id/status` | Cambiar estado |
| GET/POST | `/fairs` | Listar/crear ferias |
| PATCH | `/fairs/:id/status` | Publicar o inhabilitar |
| GET/POST | `/admin/categories`, `/categories` | Consultar/crear categorías |
| GET | `/audit` | Auditoría |

## Expositor y público

| Método | Ruta | Uso |
|---|---|---|
| GET/POST | `/exhibitor/products` | Productos propios |
| GET | `/public/fairs` | Ferias publicadas |
| GET | `/public/fairs/:slug` | Feria y expositores autorizados |
| GET | `/public/fairs/:slug/exhibitors/:id` | Productos públicos |
| POST | `/public/whatsapp-query` | Generar enlace del expositor propietario |

Errores de validación se devuelven en español sin contraseñas, hashes ni claves privadas.
