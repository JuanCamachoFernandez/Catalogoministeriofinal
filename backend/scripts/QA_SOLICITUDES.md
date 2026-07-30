# QA manual de solicitudes

## Carga de datos

Desde `backend`, con PostgreSQL y las migraciones actualizadas:

```powershell
.\.venv\Scripts\python.exe -m scripts.sembrar_solicitudes_qa
```

El script es idempotente: si los correos `qa.pendiente@gmail.com`,
`qa.aprobada@gmail.com` y `qa.rechazada@gmail.com` ya existen, no duplica los
casos. Los datos usan el prefijo `QA Solicitud` para identificarlos fácilmente.

La unidad aprobada también crea el usuario:

```text
Usuario: qa.solicitud.aprobada
Contraseña: QA.Solicitud2026!
```

## Escenarios

1. En `/admin/solicitudes`, buscar `QA Solicitud` y validar que aparezcan los
   estados Pendiente, Aprobada y Rechazada en español.
2. Filtrar por cada estado y confirmar que la tabla solo muestre el resultado
   correspondiente.
3. Abrir cada caso con `Revisar` y verificar las secciones, labels, datos de
   contacto, redes sociales y los tres productos con imagen, precio y
   descripción.
4. En el caso pendiente, aprobar y confirmar que el estado cambie y que se
   cree la unidad productiva asociada.
5. En otra ejecución limpia, rechazar el caso pendiente usando un motivo corto
   y uno largo; verificar que el botón se habilite solo cuando exista texto.
6. Confirmar el comportamiento responsive en anchos aproximados de 1280 px,
   768 px y 390 px.
7. Abrir el caso aprobado y probar `Reenviar credenciales` solo si el correo
   está deshabilitado o apuntado a un entorno de prueba.

## Limpieza

No se incluye un borrado automático para evitar afectar datos reales. Elimina
manualmente los tres casos y sus relaciones desde una base de desarrollo, o
usa una base PostgreSQL cuyo nombre termine en `_test` con `reset-test-db`.
