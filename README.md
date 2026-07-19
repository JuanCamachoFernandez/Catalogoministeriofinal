# Catálogo Digital de Ferias

Sistema web para administrar y publicar ferias, expositores, productos y categorías del sector productivo boliviano.

El proyecto utiliza Flask con PostgreSQL en el backend y React con TypeScript en el frontend. Incluye paneles diferenciados para superadministradores, administradores y expositores, además de un catálogo público para la ciudadanía.

## Funcionalidades principales

- Administración de usuarios, unidades, expositores, ferias y categorías.
- Perfil editable para superadministradores, administradores y expositores.
- Productos administrados exclusivamente por el expositor propietario.
- Galerías con múltiples imágenes, portada y orden automático.
- Imágenes de ferias y logotipos mediante URL o archivo del dispositivo.
- Varias ferias pueden publicarse simultáneamente, incluso cuando comparten las mismas fechas.
- Catálogo público organizado por tarjetas de feria, detalle de participantes y productos por expositor.
- Departamentos y municipios de Bolivia mediante listas seleccionables.
- Auditoría con usuario, acción, entidad y descripción.
- Reportes generales o filtrados en PDF y Excel.
- Recuperación de contraseña mediante un código de seis dígitos enviado por Brevo.
- Consultas de productos mediante WhatsApp con cantidades.
- Bloqueo por inactividad a los dos minutos y cierre de sesión a los cinco minutos.
- Mensajes, confirmaciones y resultados mediante modales centrales.
- Identidad visual institucional con el escudo de Bolivia centrado y una paleta basada en negro, dorado, rojo, amarillo y verde.

## Roles

- `SUPERADMIN`: administra usuarios administradores y todos los módulos.
- `ADMIN_VICEMINISTERIO`: administra expositores, ferias, categorías, auditoría y reportes; solamente consulta productos.
- `EXPOSITOR`: administra su empresa, perfil, productos e imágenes.

## Tecnologías

### Backend

- Python 3.11 o superior.
- Flask y Flask-SQLAlchemy.
- PostgreSQL 16 o superior.
- Alembic y Flask-Migrate.
- JWT para autenticación.
- Argon2 para contraseñas.
- Brevo Transactional Email mediante HTTPS.
- ReportLab y OpenPyXL para reportes.

### Frontend

- React.
- TypeScript.
- Vite.
- TanStack Query.
- Vitest.
- Playwright para pruebas de navegador.

## Estructura general

```text
CatalogoMinisterio/
├── backend/
│   ├── app/
│   │   ├── controllers/
│   │   ├── models/
│   │   └── views/
│   ├── migrations/
│   ├── tests/
│   ├── .env.example
│   └── run.py
├── frontend/
│   ├── src/
│   ├── e2e/
│   └── .env.example
└── docs/
```

El escudo utilizado por la interfaz se encuentra en `frontend/public/escudo-bolivia.png`. Los colores globales se administran desde `frontend/src/styles/theme.css` y su presentación desde `frontend/src/index.css`.

## Primera instalación

### 1. Preparar PostgreSQL

Cree una base llamada `catalogo_ferias` y un usuario con permisos sobre ella. La dirección configurada debe tener este formato:

```env
DIRECCION_BASE_DATOS=postgresql+psycopg://usuario:contrasena@localhost:5432/catalogo_ferias
```

Consulte la guía [Configuración de PostgreSQL](docs/CONFIGURACION_POSTGRESQL.md) para una instalación detallada.

### 2. Configurar el backend

Desde la raíz del proyecto:

```powershell
Copy-Item backend\.env.example backend\.env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Edite `backend/.env` antes de continuar. No utilice los valores de ejemplo en un sistema real.

Variables principales:

```env
CLAVE_SECRETA_APLICACION=genere-una-clave-aleatoria
CLAVE_SECRETA_SESIONES=genere-otra-clave-diferente
DIRECCION_BASE_DATOS=postgresql+psycopg://usuario:contrasena@localhost:5432/catalogo_ferias
DIRECCION_INTERFAZ_WEB=http://localhost:5173
ORIGENES_PERMITIDOS=http://localhost:5173
CARPETA_CARGAS=uploads
TAMANO_MAXIMO_CONTENIDO=10485760
SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA=60

USUARIO_ADMINISTRADOR_INICIAL=administrador.principal
NOMBRES_ADMINISTRADOR_INICIAL=Administrador
APELLIDO_PATERNO_ADMINISTRADOR_INICIAL=Principal
APELLIDO_MATERNO_ADMINISTRADOR_INICIAL=Sistema
CORREO_ADMINISTRADOR_INICIAL=administrador@gmail.com
CONTRASENA_ADMINISTRADOR_INICIAL=CambieEstaClave123!

CLAVE_BREVO=
CORREO_REMITENTE_BREVO=
NOMBRE_REMITENTE_BREVO=Catálogo Digital de Ferias
ENVIO_CORREO_HABILITADO=false
```

Las contraseñas deben tener al menos diez caracteres, mayúscula, minúscula, número y carácter especial. El correo inicial debe terminar en `@gmail.com`.

Para generar secretos aleatorios:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Ejecute el comando dos veces y utilice resultados diferentes.

### 3. Crear el esquema y los datos iniciales

```powershell
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-catalogs
python -m flask --app run.py seed-admin
```

`seed-admin` solamente crea el primer superadministrador. Cambiar después las variables terminadas en `_ADMINISTRADOR_INICIAL` no modifica una cuenta existente.

### 4. Configurar el frontend

En otra terminal, desde la raíz:

```powershell
Copy-Item frontend\.env.example frontend\.env
cd frontend
npm install
```

Configuración de desarrollo:

```env
VITE_DIRECCION_SERVICIO=http://localhost:5000/api
VITE_NOMBRE_APLICACION=Catálogo Digital de Ferias
VITE_CODIGO_PAIS_PREDETERMINADO=591
```

El prefijo `VITE_` es obligatorio para que Vite permita utilizar esas variables en el navegador.

## Ejecución diaria

### Terminal 1: backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m flask --app run.py run --debug --host=0.0.0.0 --port=5000
```

### Terminal 2: frontend

```powershell
cd frontend
npm run dev
```

## Direcciones locales

- Inicio de sesión: http://localhost:5173/gestion/login
- Catálogo público: http://localhost:5173/catalogo
- Estado del backend: http://localhost:5000/api/health

## Base de datos en español

El esquema físico de PostgreSQL utiliza tablas, columnas, índices y restricciones con nombres en español. La migración inicial crea, entre otras, las siguientes tablas:

```text
usuarios
perfiles_administradores
unidades_administrativas
recuperaciones_contrasena
codigos_acceso_revocados
expositores
tipos_expositor
tipos_expositor_asignados
ferias
imagenes_feria
expositores_feria
categorias
productos
imagenes_producto
auditorias
estados_memoria_temporal
version_migraciones
```

Para aplicar cambios pendientes:

```powershell
cd backend
python -m flask --app run.py db upgrade
python -m flask --app run.py db check
```

## Recuperación de contraseña y Brevo

El correo se utiliza únicamente para recuperar contraseñas. El flujo es:

1. El usuario confirma su Gmail.
2. El sistema envía un código de seis dígitos.
3. El usuario verifica el código.
4. El sistema permite establecer y confirmar una contraseña nueva.

Para habilitar el envío real, configure un remitente verificado en Brevo y cambie:

```env
ENVIO_CORREO_HABILITADO=true
```

Consulte [Configuración de Brevo](docs/CONFIGURACION_BREVO.md). Nunca publique `CLAVE_BREVO`.

## Pruebas

### Backend sin PostgreSQL externo

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q -m "not postgres"
```

### Migración real de PostgreSQL

Utilice una base separada cuyo nombre termine obligatoriamente en `_test`:

```powershell
$env:DIRECCION_BASE_DATOS_PRUEBAS="postgresql+psycopg://usuario:contrasena@localhost:5432/catalogo_ferias_test"
$env:CORREO_ADMINISTRADOR_PRUEBAS="catalogo.test@gmail.com"
$env:CONTRASENA_ADMINISTRADOR_PRUEBAS="Catalogo.Test123!"
python -m pytest -q -m postgres
```

La prueba de integración elimina y reconstruye el esquema de esa base. Nunca apunte `DIRECCION_BASE_DATOS_PRUEBAS` a la base principal. Las credenciales anteriores pertenecen únicamente a los datos temporales de prueba.

### Frontend

```powershell
cd frontend
npm.cmd test -- --run
npm.cmd run build
```

Las pruebas de navegador requieren revisar previamente la configuración de [Playwright](frontend/playwright.config.ts).

## Seguridad

- No suba `backend/.env` ni `frontend/.env` al repositorio.
- Utilice secretos y contraseñas diferentes para desarrollo, pruebas y producción.
- Revoque inmediatamente cualquier clave de Brevo que haya sido compartida o publicada.
- Restrinja `ORIGENES_PERMITIDOS` al dominio real del frontend.
- La contraseña inicial es temporal y debe cambiarse en el primer ingreso.
- Cambiar `CLAVE_SECRETA_SESIONES` invalida las sesiones abiertas.
- Mantenga una base independiente para las pruebas destructivas.

## Documentación adicional

- [Primera instalación](docs/INSTALACION_PRIMERA_VEZ.md)
- [Ejecución diaria](docs/EJECUCION_DIARIA.md)
- [Configuración para compartir](docs/CONFIGURACION_PARA_COMPARTIR.md)
- [PostgreSQL](docs/CONFIGURACION_POSTGRESQL.md)
- [Brevo](docs/CONFIGURACION_BREVO.md)
- [API](docs/API.md)
- [Arquitectura MVC](docs/ARQUITECTURA_MVC.md)
- [Seguridad](docs/SEGURIDAD.md)
- [Manual del frontend](docs/MANUAL_FRONTEND.md)
- [Matriz frontend/API](docs/MATRIZ_FRONTEND_API.md)

## Observaciones

- El backend conserva algunos identificadores internos exigidos por Flask, JWT y SQLAlchemy, como `SECRET_KEY` o `SQLALCHEMY_DATABASE_URI`. Las variables que configura el usuario están en español.
- El prefijo `VITE_` es obligatorio y no puede traducirse ni eliminarse.
- Las rutas JSON internas conservan compatibilidad con el frontend actual para evitar errores en formularios y ediciones.
