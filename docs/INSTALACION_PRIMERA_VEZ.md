# Instalación por primera vez — Windows 10/11

## 1. Programas necesarios

Instale Git, Visual Studio Code, Python 3.11+, Node.js 20 LTS+, npm y PostgreSQL 16+. Compruebe:

```powershell
git --version
python --version
node --version
npm --version
psql --version
```

## 2. Obtener el proyecto

```powershell
git clone URL_DEL_REPOSITORIO
cd CatalogoMinisterio
```

## 3. Archivos de entorno

Solo si no existen:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

No ejecute las copias sobre un `.env` ya configurado. Edite `backend/.env` con PostgreSQL, secretos, administrador inicial y Brevo; edite `frontend/.env` con `VITE_DIRECCION_SERVICIO=http://localhost:5000/api`.

Configure el primer superadministrador con estas variables privadas:

```env
USUARIO_ADMINISTRADOR_INICIAL=administrador.principal
NOMBRES_ADMINISTRADOR_INICIAL=Nombres
APELLIDO_PATERNO_ADMINISTRADOR_INICIAL=ApellidoPaterno
APELLIDO_MATERNO_ADMINISTRADOR_INICIAL=ApellidoMaterno
CORREO_ADMINISTRADOR_INICIAL=usuario@gmail.com
CONTRASENA_ADMINISTRADOR_INICIAL=UnaClaveSegura123!
```

## 4. PostgreSQL

Desde pgAdmin cree el usuario y la base siguiendo [CONFIGURACION_POSTGRESQL.md](CONFIGURACION_POSTGRESQL.md). Compruebe que `DIRECCION_BASE_DATOS` tenga usuario, contraseña, host, puerto y base correctos.

## 5. Backend

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
flask db upgrade
flask seed-catalogs
flask seed-admin
flask --app run.py run --debug --host=0.0.0.0 --port=5000
```

Si `seed-admin` informa que ya existe, no lo repita. Compruebe http://localhost:5000/api/health.

## 6. Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Si PowerShell bloquea `npm.ps1`, use `npm.cmd run dev`.

## 7. Primer acceso

- Gestión: http://localhost:5173/gestion/login
- Catálogo: http://localhost:5173/catalogo

Ingrese con el username mostrado por `seed-admin` y `CONTRASENA_ADMINISTRADOR_INICIAL`. El sistema obliga a cambiar la contraseña temporal.

## 8. Brevo

Si ya está configurado, no cambie ni copie sus credenciales. Verifique únicamente las variables descritas en [CONFIGURACION_BREVO.md](CONFIGURACION_BREVO.md). Use `ENVIO_CORREO_HABILITADO=false` mientras diagnostica problemas.

## 9. Verificación

```powershell
# backend
pytest
flask db check

# frontend
npm run test
npm run lint
npm run build
```

## Errores frecuentes

- `npm no se reconoce`: instale Node LTS y reinicie VS Code.
- Activación bloqueada: use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- Conexión PostgreSQL rechazada: revise servicio, contraseña, puerto 5432 y `DIRECCION_BASE_DATOS`.
- Tabla inexistente: ejecute `flask db upgrade`.
- CORS: confirme que frontend use puerto 5173 y `ORIGENES_PERMITIDOS` coincida.
- Brevo: confirme API key, remitente verificado y conexión, sin mostrar valores.
- Puerto ocupado: cierre el proceso anterior o inicie con otro puerto y actualice las URLs.

## Linux y macOS

Use `python3 -m venv .venv`, active con `source .venv/bin/activate` y cambie `Copy-Item` por `cp`. Los demás comandos son equivalentes.
