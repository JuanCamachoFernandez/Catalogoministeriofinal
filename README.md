# Catálogo Digital de Ferias

Aplicación web para registrar Unidades Productivas, administrar ferias y publicar automáticamente sus productos en un catálogo público.

El sistema tiene un backend Flask con PostgreSQL y un frontend React con TypeScript. La participación se asigna a una Unidad Productiva completa: cuando está autorizada en una feria activa, sus productos publicables aparecen automáticamente en el catálogo.

## Tecnologías

- Backend: Python 3.11+, Flask, SQLAlchemy, Alembic, JWT y PostgreSQL 16+.
- Frontend: React 19, TypeScript, Vite y TanStack Query.
- Pruebas: Pytest, Vitest y Playwright.
- Integraciones: Brevo para correos y WhatsApp para consultas de productos.

## Requisitos

Instale antes de comenzar:

- Git.
- Python 3.11 o superior.
- Node.js 20 LTS o superior y npm.
- PostgreSQL 16 o superior.

Compruebe las instalaciones:

```powershell
git --version
python --version
node --version
npm --version
psql --version
```

## Instalación por primera vez

Los comandos principales están escritos para PowerShell en Windows. En Linux o macOS use `python3`, active el entorno con `source .venv/bin/activate` y reemplace `Copy-Item` por `cp`.

### 1. Descargar el proyecto

```powershell
git clone https://github.com/mich-rp/CatalogoMinisterio.git
cd CatalogoMinisterio
```

### 2. Crear PostgreSQL

Desde pgAdmin o `psql`, cree un usuario y la base local:

```sql
CREATE USER catalogo WITH PASSWORD 'CONTRASENA_LOCAL_SEGURA';
CREATE DATABASE catalogo_ferias OWNER catalogo;
GRANT ALL PRIVILEGES ON DATABASE catalogo_ferias TO catalogo;
```

Si la contraseña contiene caracteres especiales reservados para URL, deberá codificarlos en la cadena de conexión.

### 3. Configurar el backend

Desde la raíz del repositorio:

```powershell
Copy-Item backend\.env.example backend\.env
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Edite `backend/.env`. Como mínimo, cambie:

```env
CLAVE_SECRETA_APLICACION=SECRETO_ALEATORIO_1
CLAVE_SECRETA_SESIONES=SECRETO_ALEATORIO_2
DIRECCION_BASE_DATOS=postgresql+psycopg://catalogo:CONTRASENA_LOCAL_SEGURA@localhost:5432/catalogo_ferias
DIRECCION_INTERFAZ_WEB=http://localhost:5173
ORIGENES_PERMITIDOS=http://localhost:5173

USUARIO_ADMINISTRADOR_INICIAL=administrador.principal
NOMBRES_ADMINISTRADOR_INICIAL=Administrador
APELLIDO_PATERNO_ADMINISTRADOR_INICIAL=Principal
APELLIDO_MATERNO_ADMINISTRADOR_INICIAL=Sistema
CORREO_ADMINISTRADOR_INICIAL=administrador@gmail.com
CONTRASENA_ADMINISTRADOR_INICIAL=CambieEstaClave123!
```

Genere cada secreto por separado:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

No use en producción los secretos ni las contraseñas del archivo de ejemplo.

### 4. Preparar la base de datos

Con el entorno virtual activado y dentro de `backend`:

```powershell
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-catalogs
python -m flask --app run.py seed-productive-sectors
python -m flask --app run.py seed-admin
python -m flask --app run.py db check
```

`seed-admin` crea solamente el primer superadministrador. Si informa que ya existe, no necesita repetirlo. Las migraciones son la fuente oficial del esquema; no cree tablas manualmente.

### 5. Configurar el frontend

Abra otra terminal desde la raíz del repositorio:

```powershell
Copy-Item frontend\.env.example frontend\.env
cd frontend
npm ci
```

La configuración local predeterminada es:

```env
VITE_DIRECCION_SERVICIO=http://localhost:5000/api
VITE_NOMBRE_APLICACION=Catálogo Digital de Ferias
VITE_CODIGO_PAIS_PREDETERMINADO=591
```

### 6. Iniciar el proyecto

Terminal 1 — backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m flask --app run.py run --debug --host=0.0.0.0 --port=5000
```

Terminal 2 — frontend:

```powershell
cd frontend
npm run dev
```

Compruebe:

- Inicio de sesión: <http://localhost:5173/login>
- Solicitud pública: <http://localhost:5173/solicitud-registro>
- Catálogo público: <http://localhost:5173/catalogo>
- Administración: <http://localhost:5173/admin>
- Portal de la Unidad Productiva: <http://localhost:5173/unidad-productiva>
- Estado del backend: <http://localhost:5000/api/health>

En el primer acceso, el administrador debe cambiar su contraseña temporal.

## Trabajo diario

No vuelva a crear la base, el entorno virtual ni los archivos `.env` cada día.

### Inicio rápido después de la primera instalación

Abra dos terminales en la raíz del repositorio.

Terminal 1 — API Flask:

```powershell
cd backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m flask --app run.py db upgrade
python -m flask --app run.py run --debug --host=0.0.0.0 --port=5000
```

Terminal 2 — interfaz React:

```powershell
cd frontend
npm run dev
```

No ejecute `npm ci`, los comandos `seed-*` ni vuelva a crear `.venv` en cada inicio. Úselos solamente durante la primera instalación o cuando cambien las dependencias o datos iniciales.

### 1. Actualizar el código

Antes de descargar cambios, confirme que no tiene trabajo sin guardar:

```powershell
git status
git pull --ff-only
```

Para una tarea nueva, trabaje en una rama propia:

```powershell
git switch -c feat/nombre-corto
```

Use prefijos como `feat/`, `fix/`, `docs/` o `test/`. Evite desarrollar directamente sobre `main`.

### 2. Aplicar cambios recibidos

Después de un `git pull`:

```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
# Solo si cambió backend/requirements.txt
python -m pip install -r requirements.txt
# Después de recibir cambios, aplique las migraciones pendientes
python -m flask --app run.py db upgrade

# Frontend: solo si cambió frontend/package-lock.json
cd ..\frontend
npm ci
```

`pip install` y `npm ci` no son necesarios en cada inicio si sus archivos de dependencias no cambiaron.

### 3. Levantar los servidores

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m flask --app run.py run --debug --host=0.0.0.0 --port=5000
```

Frontend, en otra terminal:

```powershell
cd frontend
npm run dev
```

Detenga cada servidor con `Ctrl+C`. Para salir del entorno de Python use `deactivate`.

### 4. Verificar antes de entregar

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q -m "not postgres"
python -m flask --app run.py db check
```

Frontend:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Finalmente revise y guarde su trabajo:

```powershell
git status
git diff --check
git add RUTA_DE_LOS_ARCHIVOS
git commit -m "tipo: descripción breve"
git push -u origin NOMBRE_DE_LA_RAMA
```

No use `git add .` sin revisar antes qué archivos serán incluidos.

## Cambios de base de datos

Cuando cambie un modelo SQLAlchemy:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m flask --app run.py db migrate -m "Descripción concreta"
python -m flask --app run.py db upgrade
python -m flask --app run.py db check
```

Revise siempre el archivo generado dentro de `backend/migrations/versions/`. No elimine ni reescriba migraciones que ya hayan sido compartidas o aplicadas sin coordinarlo con el equipo.

### Pruebas PostgreSQL destructivas

La integración desde cero requiere una base separada cuyo nombre termine en `_test`:

```powershell
$env:DIRECCION_BASE_DATOS_PRUEBAS="postgresql+psycopg://catalogo:CONTRASENA@localhost:5432/catalogo_ferias_test"
cd backend
python -m pytest -q -m postgres
```

Esta prueba elimina y reconstruye el esquema de la base indicada. Nunca configure `DIRECCION_BASE_DATOS_PRUEBAS` con `catalogo_ferias` ni con una base que contenga información real.

## Estructura del repositorio

```text
CatalogoMinisterio/
├── backend/
│   ├── app/
│   │   ├── controllers/   # Rutas y coordinación HTTP
│   │   ├── models/        # Entidades y reglas de dominio
│   │   └── views/         # Validación y serialización JSON
│   ├── migrations/        # Versionado de PostgreSQL
│   └── tests/             # Pruebas Pytest
├── frontend/
│   ├── src/               # Aplicación React
│   └── e2e/               # Pruebas Playwright
└── docs/                  # Manuales técnicos y funcionales
```

El backend sigue MVC explícito y no utiliza una carpeta `services`. La API canónica trabaja con `ProductiveUnit`, `ProductiveSector`, `Product`, `Fair` y `FairParticipation`. Algunas rutas anteriores siguen disponibles temporalmente por compatibilidad con el frontend.

## Reglas importantes del catálogo

- Una feria no puede superponerse con otra feria no terminal.
- La participación pertenece a toda la Unidad Productiva; no se seleccionan productos individualmente.
- Una Unidad Productiva necesita al menos tres productos publicables para aparecer.
- Cada producto necesita exactamente tres imágenes y una sola portada.
- Solo productos `AVAILABLE` u `OUT_OF_STOCK` aparecen públicamente.
- Ferias `FINISHED` o `DISABLED` son terminales e inmutables.
- Las eliminaciones principales son lógicas y conservan el historial.

## Variables, archivos y seguridad

- Nunca suba `backend/.env`, `frontend/.env`, claves de Brevo, contraseñas ni respaldos.
- `backend/uploads/`, los entornos virtuales y `frontend/node_modules/` son locales y no deben versionarse.
- Mantenga bases distintas para desarrollo, pruebas y producción.
- Configure `ENVIO_CORREO_HABILITADO=false` hasta disponer de un remitente verificado en Brevo.
- Cambiar `CLAVE_SECRETA_SESIONES` invalida todas las sesiones JWT.
- Antes de actualizar o eliminar datos reales, realice un respaldo de PostgreSQL.

## Problemas frecuentes

- PowerShell bloquea la activación: ejecute `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- `npm.ps1` está bloqueado: use `npm.cmd run dev` o habilite scripts para la sesión.
- PostgreSQL rechaza la conexión: revise que el servicio esté iniciado, el puerto 5432 y `DIRECCION_BASE_DATOS`.
- Faltan tablas o columnas: ejecute `python -m flask --app run.py db upgrade`.
- El navegador muestra un error CORS: verifique `ORIGENES_PERMITIDOS` y `VITE_DIRECCION_SERVICIO`.
- Un puerto está ocupado: detenga el proceso anterior o cambie el puerto y las URLs relacionadas.

## Documentación

- [Instalación detallada](docs/INSTALACION_PRIMERA_VEZ.md)
- [Ejecución diaria](docs/EJECUCION_DIARIA.md)
- [Configuración de PostgreSQL](docs/CONFIGURACION_POSTGRESQL.md)
- [Configuración de Brevo](docs/CONFIGURACION_BREVO.md)
- [Contrato de la API](docs/API.md) y [OpenAPI](docs/openapi.yaml)
- [Arquitectura MVC](docs/ARQUITECTURA_MVC.md)
- [Seguridad](docs/SEGURIDAD.md)
- [Configuración de producción](docs/CONFIGURACION_PRODUCCION.md)
