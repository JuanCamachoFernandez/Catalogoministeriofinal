# Reorganización del proyecto

## Convención

Las carpetas y archivos propios usan español, minúsculas y guiones cuando hay
más de una palabra. Se conservan nombres técnicos obligatorios (`__init__.py`,
`main.tsx`, `App.tsx`, `index.ts`, `README.md`) y valores que forman parte de
contratos externos, como roles, campos JSON, URLs y nombres de tablas.

## Frontend

```text
frontend/src/
├── aplicacion/{disenios,proveedores,rutas}
├── modulos/
│   ├── administracion
│   ├── autenticacion
│   ├── catalogo-publico
│   ├── registro
│   ├── reportes
│   └── unidad-productiva
├── compartido/
│   ├── autenticacion
│   ├── componentes
│   ├── constantes
│   ├── estilos
│   ├── ganchos
│   ├── servicios
│   ├── tipos
│   ├── utilidades
│   └── validaciones
└── main.tsx
```

No quedan carpetas inglesas o históricas paralelas. Las implementaciones de
portal antiguo fueron eliminadas tras comprobar que no tenían rutas, imports ni
pruebas. `api.ts` y `ui.tsx` se conservan únicamente como API pública; los imports
internos apuntan a `compartido`.

## Backend

```text
backend/app/
├── autenticacion
├── controladores
├── errores
├── esquemas
├── modelos
├── repositorios
├── rutas
├── serializadores
├── servicios
├── validadores
├── configuracion.py
├── extensiones.py
└── __init__.py
```

Los Blueprints y sus prefijos se conservan. Las rutas mantienen métodos,
parámetros, códigos y JSON. Los servicios transversales se separaron por
responsabilidad; no existe un archivo genérico `common.py`, `helpers.py` o
`utils.py`. Los esquemas y serializadores ya no están mezclados en `views`.

Flask-SQLAlchemy y SQLAlchemy continúan siendo el ORM oficial. La instancia única
`db` y Flask-Migrate viven en `backend/app/extensiones.py`; los 23 modelos/tablas
administrados se registran desde `backend/app/modelos/__init__.py`. Desarrollo y
producción crean o actualizan PostgreSQL mediante `flask db upgrade`. Solo las
pruebas aisladas usan `db.create_all()` sobre SQLite temporal.

## Agregar roles y permisos

En frontend se actualiza `compartido/autenticacion/roles.ts`. En backend se crea
o reutiliza una política de `autenticacion/permisos.py` y se aplica con el
decorador central. La autorización siempre consulta el rol almacenado en la base.

## Agregar servicios y repositorios

Un repositorio encapsula consultas SQLAlchemy reutilizables y no conoce Flask. Un
servicio coordina repositorios, transacciones y reglas de negocio. Los
controladores preparan respuestas HTTP; las rutas definen endpoints y permisos.
Una consulta pequeña y exclusiva puede permanecer en la ruta cuando extraerla
aporte más complejidad que claridad. Un endpoint heredado debe llamar a la misma
operación canónica.

## Operación

```powershell
cd backend
$env:DIRECCION_BASE_DATOS="postgresql+psycopg://usuario:clave@localhost:5432/catalogo_ferias"
.\.venv\Scripts\flask.exe --app app:create_app db upgrade
.\.venv\Scripts\flask.exe --app app:create_app seed-catalogs
.\.venv\Scripts\flask.exe --app app:create_app seed-productive-sectors
.\.venv\Scripts\flask.exe --app app:create_app run

cd ..\frontend
npm.cmd run dev
```

Los datos de demostración se cargan desde `backend/` con
`.\.venv\Scripts\python.exe -m scripts.sembrar_demo_publica`. La guía detallada
para modelos, repositorios, servicios, endpoints y pruebas está en
`backend/README.md`.

## Compatibilidad y riesgos

- No se cambiaron migraciones, tablas, columnas, relaciones ni datos.
- No se cambiaron endpoints ni valores de roles.
- Los JWT siguen en `localStorage`; las cookies HttpOnly requieren otra versión
  coordinada del contrato.
- `estilos-base.css` conserva reglas históricas globales para evitar cambios de
  cascada y deberá dividirse con regresión visual automatizada.
- Algunos controladores de dominio grandes continúan junto a sus decoradores de
  ruta; sus consultas deben migrarse incrementalmente siguiendo la arquitectura
  documentada, evitando una reescritura masiva de comportamiento estable.
- Las migraciones existentes están orientadas a PostgreSQL. SQLite se usa solo
  con `create_all()` en pruebas y no como destino de la cadena Alembic.

## Validación

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -m "not postgres"

cd ..\frontend
npm.cmd run lint
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e -- --project=chromium-desktop

cd ..
git diff --check
```
