# Carga final de producción

Estos comandos son deliberadamente independientes. `reset-produccion` nunca llama a
Cloudinary, `limpiar-cloudinary-produccion` nunca toca PostgreSQL y el importador
nunca envía correo ni genera credenciales recuperables.

## Fuentes aceptadas

La fuente general se lee directamente con Google Sheets API. Se reconocen encabezados
en español para identidad, contacto, representante, ubicación, reseña, sectores,
logo y productos. Un campo libre de productos solo se separa si contiene saltos de
línea, punto y coma o numeración inequívoca; una coma nunca es separador.

La fuente corregida puede tener el mismo formato o cuatro hojas relacionales cuyos
nombres contengan `Unidades`, `Sectores`, `Productos` e `Imagenes`. Las asociaciones
usan `ID/Codigo unidad` y `ID/Codigo producto` (también se admite el nombre como
clave). Las imágenes deben contener un Drive ID o enlace Drive. El dry-run reporta
filas inválidas y conflictos; no los completa ni los importa.

## Comandos

Desde el directorio `backend`, con las variables de producción ya inyectadas:

```sh
flask --app app:create_app reset-produccion --dry-run
flask --app app:create_app reset-produccion --confirm RESET-PRODUCTION
flask --app app:create_app db upgrade
flask --app app:create_app seed-inicial

flask --app app:create_app limpiar-cloudinary-produccion --dry-run
flask --app app:create_app limpiar-cloudinary-produccion --confirm DELETE-CLOUDINARY

flask --app app:create_app importar-datos-finales --sheet-general ID_GENERAL --sheet-corregidos ID_CORREGIDOS --dry-run --report /tmp/importacion-plan.json
flask --app app:create_app importar-datos-finales --commit --plan /secrets/importacion-plan.json --report /tmp/importacion-resultado.json
```

Antes de usar `--commit`, el plan debe revisarse y montarse sin modificaciones. El
commit vuelve a descargar ambas hojas y rechaza el plan si cambió cualquier celda.

## Entorno del seed

- `CORREO_ADMINISTRADOR_INICIAL`
- `CONTRASENA_ADMINISTRADOR_INICIAL`
- `NOMBRES_ADMINISTRADOR_INICIAL`
- `APELLIDO_PATERNO_ADMINISTRADOR_INICIAL`
- `APELLIDO_MATERNO_ADMINISTRADOR_INICIAL` (opcional)
- `USUARIO_ADMINISTRADOR_INICIAL` (opcional)

## Entorno del importador

- `DIRECCION_BASE_DATOS` o `DATABASE_URL`
- `CLOUDINARY_URL` (o las tres variables Cloudinary equivalentes)
- `GOOGLE_IMPORT_TOKEN_PATH=/secrets/google-import-token.json`
- secret file OAuth de solo lectura en `/secrets/google-import-token.json`
- para el commit, secret file revisado en `/secrets/importacion-plan.json`

El token Google debe contener únicamente `spreadsheets.readonly` y `drive.readonly`.
No se necesita Brevo y se recomienda no inyectar sus secretos en el Job.

## Job temporal Northflank

- Tipo: **Manual job**, sin schedule.
- Imagen: exactamente la misma versión ya validada del backend.
- Working directory: `/app/backend` (ajustar solo si la imagen usa otra ruta).
- Command override: el comando `--commit` mostrado arriba.
- Run on image change: **Never** (`runOnSourceChange=never`).
- Retry/backoff: **0**.
- Time limit: **3600 segundos** o más (`activeDeadlineSeconds=3600`).
- Red/secret group: la misma conexión PostgreSQL y Cloudinary del backend.
- Secret files: token Google y plan en las rutas indicadas.
- Recursos: al menos los mismos CPU/RAM que el backend; almacenamiento efímero de 1 GiB.

Northflank solo aplica `Concurrency: Forbid` a cron jobs, no a ejecuciones manuales.
Este Job debe permanecer manual; el importador usa además un advisory lock global de
PostgreSQL y rechaza una segunda ejecución concurrente. Tras revisar el reporte y el
estado `COMPLETED`, eliminar el Job y ambos secret files temporales.
