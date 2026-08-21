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

El lector busca la fila de encabezados entre las primeras 20 filas y normaliza
mayúsculas, tildes, guiones, signos de pregunta, saltos de línea y guiones bajos.
Las columnas vacías intermedias no desplazan las siguientes columnas. El esquema
canónico aceptado es:

- Formulario general: `Nombre comercial`/`Nombre de la unidad productiva`, `Razon
  social`, `NIT` (opcional), `Correo electronico`, `Telefono/WhatsApp`, representante
  en tres columnas o `Nombre completo del representante`, `Departamento`, `Direccion
  fisica`, `Resena comercial`, sectores, logo y productos (estos tres últimos no
  invalidan por sí solos a la unidad).
- `Unidades`: los mismos campos de unidad; puede incluir `ID/Codigo unidad`.
- `Sectores`: `ID/Codigo unidad` o `Nombre comercial`, y `Sector`/`Nombre sector`.
- `Productos`: `ID/Codigo unidad` o `Nombre comercial`, `ID/Codigo producto`,
  `Nombre producto` y `Descripcion` (la descripción puede faltar: queda `DRAFT`).
- `Imagenes`: `ID/Codigo producto` o `Nombre producto`, y `Drive ID`/`URL`.

La pestaña `Unidades` se procesa independientemente de `Productos`, `Sectores` e
`Imagenes`: la ausencia o incompletitud de un producto nunca convierte a su unidad
en inválida. El NIT vacío también es válido.

El resumen del dry-run separa productos del formulario y de la plantilla corregida.
En `Productos`, `filas leídas` cuenta todas las filas no vacías; `detectados` requiere
un nombre; `importables` requiere además una unidad relacionada y válida. La falta de
descripción, precio, presentación, capacidad/stock o imágenes conserva el producto
como `DRAFT`. Las advertencias se agrupan por motivo y severidad, y los errores de
unidad muestran únicamente fuente y número de fila.

Las métricas de imágenes se calculan usando los Drive IDs y referencias presentes en
las hojas. El dry-run no descarga archivos ni realiza operaciones en Cloudinary.

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
