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
| `CLAVE_SECRETA_APLICACION` | Cadena aleatoria larga para Flask |
| `CLAVE_SECRETA_SESIONES` | Otra cadena aleatoria distinta |
| `DIRECCION_BASE_DATOS` | Usuario, contraseña, host, puerto y base PostgreSQL |
| `DIRECCION_INTERFAZ_WEB` | `http://localhost:5173` en desarrollo |
| `ORIGENES_PERMITIDOS` | Orígenes frontend permitidos, separados por coma |
| `CARPETA_CARGAS` | `uploads` para almacenamiento local |
| `TAMANO_MAXIMO_CONTENIDO` | Máximo de carga en bytes |
| Variables terminadas en `_ADMINISTRADOR_INICIAL` | Datos del primer SUPERADMIN |
| `CLAVE_BREVO` | Clave de la API HTTP de Brevo |
| `CORREO_REMITENTE_BREVO` | Dirección remitente verificada en Brevo |
| `NOMBRE_REMITENTE_BREVO` | Nombre que verá quien recibe el correo |
| `ENVIO_CORREO_HABILITADO` | `true` para enviar; `false` durante configuración/pruebas |

Para generar claves locales desde PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ejecute el comando dos veces y use valores distintos.

## Frontend (`frontend/.env`)

Mantenga `VITE_DIRECCION_SERVICIO=http://localhost:5000/api` si Flask usa el puerto 5000. `VITE_NOMBRE_APLICACION` cambia el nombre visible y `VITE_CODIGO_PAIS_PREDETERMINADO=591` conserva Bolivia.

## PostgreSQL

Instale PostgreSQL 16 desde https://www.postgresql.org/download/windows/. Durante la instalación guarde la contraseña del usuario `postgres`. Desde pgAdmin o `psql`, cree un usuario y base:

```sql
CREATE USER catalogo WITH PASSWORD 'CAMBIAR_ESTA_CONTRASENA';
CREATE DATABASE catalogo_ferias OWNER catalogo;
GRANT ALL PRIVILEGES ON DATABASE catalogo_ferias TO catalogo;
```

Después configure:

```env
DIRECCION_BASE_DATOS=postgresql+psycopg://catalogo:CAMBIAR_ESTA_CONTRASENA@localhost:5432/catalogo_ferias
```

Cada computadora puede tener una contraseña PostgreSQL distinta.

## API HTTP de Brevo (sin SMTP)

1. Cree una cuenta gratuita en https://www.brevo.com/.
2. Confirme su cuenta y agregue/verifique un remitente en **Settings → Senders & IP**.
3. Abra **Settings → SMTP & API → API Keys** y genere una clave API v3.
4. Copie la clave en `CLAVE_BREVO` y el correo verificado en `CORREO_REMITENTE_BREVO`.
5. Establezca `ENVIO_CORREO_HABILITADO=true` únicamente cuando la cuenta y el remitente estén verificados.

Brevo se consume por HTTPS desde `backend/app/email_service.py`; el sistema no usa SMTP. El plan gratuito tiene un límite de 300 mensajes diarios. No suba la clave API a Git.
