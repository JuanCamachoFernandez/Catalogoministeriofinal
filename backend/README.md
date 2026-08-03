# Arquitectura y operación del backend

El backend conserva Flask-SQLAlchemy y SQLAlchemy como ORM oficial. Flask-Migrate
y Alembic administran el esquema PostgreSQL existente; no se reemplazan por SQL
manual ni por otro ORM.

## Capas

- `modelos/`: clases SQLAlchemy, tablas, columnas, relaciones y enumeraciones.
- `repositorios/`: consultas SQLAlchemy reutilizables y sin dependencias HTTP.
- `servicios/`: reglas de negocio, transacciones, auditoría, archivos y correo.
- `controladores/`: adaptación de resultados y construcción de respuestas HTTP.
- `rutas/`: Blueprints, URLs, métodos, entrada HTTP y políticas de acceso.
- `esquemas/`: carga y validación Marshmallow por dominio.
- `serializadores/`: respuestas de entidades y paginación.
- `validadores/`: validaciones comunes de solicitudes.
- `autenticacion/`: sesión, decoradores, errores JWT y matriz de permisos.
- `errores/`: formato y manejadores centralizados de errores API.
- `configuracion.py`: variables y validación segura del entorno.
- `extensiones.py`: instancia única `db`, `migrate` y `jwt`.

Una consulta pequeña utilizada una sola vez puede permanecer en una ruta si
extraerla añade más indirección que claridad. Las consultas reutilizables o las
operaciones extensas deben migrarse incrementalmente a `repositorios/` y
`servicios/`, con pruebas que preserven el contrato HTTP.

## Configurar la conexión

Desde `backend/`, crear el entorno y las variables necesarias:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DIRECCION_BASE_DATOS="postgresql+psycopg://usuario:clave@localhost:5432/catalogo_ferias"
$env:ENTORNO_APLICACION="desarrollo"
$env:CLAVE_SECRETA_APLICACION="una-clave-segura"
$env:CLAVE_SECRETA_SESIONES="otra-clave-segura"
```

También se acepta `DATABASE_URL`. Las URLs `postgres://` y `postgresql://` se
normalizan al driver `postgresql+psycopg://`. Producción rechaza los secretos y
la conexión local predeterminados.

## Crear y migrar la base de datos

Desarrollo y producción deben usar las migraciones:

```powershell
.\.venv\Scripts\flask.exe --app app:create_app db upgrade
.\.venv\Scripts\flask.exe --app app:create_app db current
```

La cadena tiene una sola cabeza y usa la tabla estándar `alembic_version`. Las
migraciones están orientadas a PostgreSQL y conservan sus restricciones,
índices y tipos. No se ejecuta `create_all()` al iniciar la aplicación ni durante
una solicitud.

Las pruebas unitarias usan SQLite temporal y `db.create_all()`/`db.drop_all()`
desde `tests/conftest.py`; esto permite aislar cada prueba sin sustituir el flujo
de migraciones de PostgreSQL. El comando destructivo `reset-test-db --yes` solo
acepta una base PostgreSQL cuyo nombre termine en `_test`.

## Datos iniciales y demostración

Los comandos son idempotentes:

```powershell
.\.venv\Scripts\flask.exe --app app:create_app seed-admin
.\.venv\Scripts\flask.exe --app app:create_app seed-catalogs
.\.venv\Scripts\flask.exe --app app:create_app seed-productive-sectors
```

Los scripts se ejecutan como módulos desde `backend/`, después de aplicar las
migraciones y cargar un administrador:

```powershell
.\.venv\Scripts\python.exe -m scripts.sembrar_demo_publica
.\.venv\Scripts\python.exe -m scripts.sembrar_solicitudes_qa
```

El demo público requiere al menos tres imágenes entre `uploads/ferias`,
`uploads/logos` y `uploads/productos`. Ambos scripts comprueban registros
existentes para no duplicarlos al ejecutarse nuevamente.

## Ejecutar el backend

```powershell
.\.venv\Scripts\flask.exe --app app:create_app run
```

## Añadir funcionalidad

Para añadir un modelo, definirlo en `modelos/<dominio>.py`, exportarlo desde
`modelos/__init__.py`, crear una migración revisada y probarla sobre PostgreSQL.

Para añadir un repositorio, colocar búsquedas, filtros o paginación reutilizable
en `repositorios/<dominio>.py`. Un repositorio puede usar `select()`,
`Modelo.query`, `db.session`, `joinedload()` y demás API de SQLAlchemy, pero no
debe construir respuestas Flask.

Para añadir un servicio, coordinar repositorios, validaciones de negocio y la
transacción en `servicios/<dominio>.py`. El `commit()` se realiza cuando toda la
operación está lista y los errores controlados deben restaurar la sesión cuando
corresponda.

Para añadir un endpoint:

1. Definir su esquema de entrada en `esquemas/`.
2. Reutilizar o crear repositorios y servicios.
3. Preparar la respuesta en `controladores/` cuando no sea trivial.
4. Declarar URL, método y política en `rutas/`.
5. Registrar un Blueprint nuevo una sola vez en `rutas/__init__.py`.
6. Agregar pruebas sin cambiar contratos o endpoints heredados.

Los permisos viven en `autenticacion/permisos.py`. El decorador carga nuevamente
al usuario desde la base y nunca confía en un rol recibido del frontend.

## Seguridad

- `/uploads/<path>` solo publica carpetas de `CARPETAS_PUBLICAS_CARGAS`.
- Las imágenes se validan por extensión, contenido y tamaño global de solicitud.
- Los errores API y JWT no exponen trazas en producción.
- Las contraseñas usan Argon2 y los tokens admiten revocación y versión de sesión.
- Los JWT permanecen en `localStorage` por compatibilidad; migrarlos a cookies
  HttpOnly requiere una versión coordinada del contrato.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not postgres"
```

Para validar migraciones PostgreSQL se configura exclusivamente una base segura
terminada en `_test`:

```powershell
$env:DIRECCION_BASE_DATOS_PRUEBAS="postgresql+psycopg://usuario:clave@localhost:5432/catalogo_ferias_test"
.\.venv\Scripts\python.exe -m pytest -q -m postgres
```

Esa prueba elimina y reconstruye el esquema indicado. Nunca debe apuntar a una
base con datos reales.

## Deuda técnica controlada

Los módulos grandes de `rutas/administracion.py`, `autenticacion.py`,
`categorias.py`, `expositores.py`, `ferias.py`, `portal_publico.py`,
`productos.py`, `reportes.py`, `sectores_productivos.py`,
`solicitudes_registro.py` y `unidades_productivas.py` todavía contienen consultas
de dominio. Deben extraerse por operaciones cubiertas por pruebas, no mediante
una reescritura masiva.
