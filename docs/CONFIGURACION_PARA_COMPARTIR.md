# Configuración para compartir el proyecto

## Archivos que sí se suben a Git

- `backend/.env.example`: plantilla del backend sin secretos.
- `frontend/.env.example`: plantilla del frontend.
- Código, migraciones, documentación y pruebas.

## Archivos que cada integrante crea localmente

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

No publique `backend/.env` si contiene contraseñas, claves JWT o tokens de Google. Envíe esos valores a su compañera mediante un canal privado, o permita que cada una use sus propias credenciales locales.

## Backend (`backend/.env`)

| Variable | Qué colocar |
|---|---|
| `SECRET_KEY` | Cadena aleatoria larga para Flask |
| `JWT_SECRET_KEY` | Otra cadena aleatoria distinta |
| `DATABASE_URL` | Usuario, contraseña, host, puerto y base PostgreSQL |
| `FRONTEND_URL` | `http://localhost:5173` en desarrollo |
| `CORS_ORIGINS` | Orígenes frontend permitidos, separados por coma |
| `UPLOAD_FOLDER` | `uploads` para almacenamiento local |
| `MAX_CONTENT_LENGTH` | Máximo de carga en bytes |
| `INITIAL_ADMIN_*` | Datos del primer SUPERADMIN |
| `BREVO_API_KEY` | Clave de la API HTTP de Brevo |
| `BREVO_SENDER_EMAIL` | Dirección remitente verificada en Brevo |
| `BREVO_SENDER_NAME` | Nombre que verá quien recibe el correo |
| `EMAIL_ENABLED` | `true` para enviar; `false` durante configuración/pruebas |

Para generar claves locales desde PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ejecute el comando dos veces y use valores distintos.

## Frontend (`frontend/.env`)

Mantenga `VITE_API_URL=http://localhost:5000/api` si Flask usa el puerto 5000. `VITE_APP_NAME` cambia el nombre visible y `VITE_DEFAULT_COUNTRY_CODE=591` conserva Bolivia.

## PostgreSQL

Instale PostgreSQL 16 desde https://www.postgresql.org/download/windows/. Durante la instalación guarde la contraseña del usuario `postgres`. Desde pgAdmin o `psql`, cree un usuario y base:

```sql
CREATE USER catalogo WITH PASSWORD 'CAMBIAR_ESTA_CONTRASENA';
CREATE DATABASE catalogo_ferias OWNER catalogo;
GRANT ALL PRIVILEGES ON DATABASE catalogo_ferias TO catalogo;
```

Después configure:

```env
DATABASE_URL=postgresql+psycopg://catalogo:CAMBIAR_ESTA_CONTRASENA@localhost:5432/catalogo_ferias
```

Cada computadora puede tener una contraseña PostgreSQL distinta.

## API HTTP de Brevo (sin SMTP)

1. Cree una cuenta gratuita en https://www.brevo.com/.
2. Confirme su cuenta y agregue/verifique un remitente en **Settings → Senders & IP**.
3. Abra **Settings → SMTP & API → API Keys** y genere una clave API v3.
4. Copie la clave en `BREVO_API_KEY` y el correo verificado en `BREVO_SENDER_EMAIL`.
5. Establezca `EMAIL_ENABLED=true` únicamente cuando la cuenta y el remitente estén verificados.

Brevo se consume por HTTPS desde `backend/app/email_service.py`; el sistema no usa SMTP. El plan gratuito tiene un límite de 300 mensajes diarios. No suba la clave API a Git.
