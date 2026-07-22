# Plan de desarrollo del backend MVC

## Resumen

El desarrollo se concentrará inicialmente en completar el backend y estabilizar su contrato HTTP antes de continuar con la adaptación del frontend en React.

La primera etapa consistirá en reorganizar la aplicación bajo una arquitectura MVC explícita, manteniendo temporalmente el comportamiento y las rutas existentes. Una vez finalizado y validado el refactor, se implementarán las solicitudes públicas de registro de Unidades Productivas, su revisión y aprobación, la generación de credenciales, la gestión de sectores y productos, la administración automática de ferias, el catálogo público, las notificaciones, la seguridad, la auditoría y las pruebas automáticas.

El backend utilizará Flask, SQLAlchemy, Marshmallow y PostgreSQL. No se incorporará una capa adicional de servicios.

## Regla principal del catálogo por ferias

La participación en una feria se asignará a la Unidad Productiva completa mediante FairParticipation.

No se creará FairProduct ni ninguna tabla intermedia para seleccionar productos individualmente por feria.

Cuando una Unidad Productiva sea autorizada para participar en una feria, todos sus productos vigentes y publicables se mostrarán automáticamente en el catálogo correspondiente.

La consulta pública seguirá la relación:

Fair → FairParticipation → ProductiveUnit → Product

Cada Unidad Productiva podrá tener como máximo cinco productos vigentes y deberá contar con al menos tres productos publicables para aparecer en el catálogo.

Los productos AVAILABLE y OUT_OF_STOCK podrán mostrarse públicamente. Los productos DRAFT, RETIRED o eliminados quedarán excluidos automáticamente.

Los cambios de nombre, descripción, precio, disponibilidad e imágenes deberán reflejarse inmediatamente en el catálogo de la feria activa sin modificar la participación.

## Terminología del dominio

- User: Usuario.
- RegistrationRequest: Solicitud de Registro.
- ProductiveUnit: Unidad Productiva.
- ProductiveSector: Sector Productivo.
- UnitSector: relación entre Unidad Productiva y Sector Productivo.
- Product: Producto.
- ProductImage: Imagen de Producto.
- Fair: Feria.
- FairParticipation: participación de una Unidad Productiva en una feria.
- Audit: registro de auditoría.

No se creará una entidad RedSocial. Facebook, Instagram y TikTok serán atributos opcionales de RegistrationRequest y ProductiveUnit.

## Decisiones generales

- El backend se completará antes de modificar el frontend.
- MVC será explícito y estricto.
- No se añadirá una carpeta services.
- Las reglas de negocio estarán principalmente en los modelos.
- Los controladores coordinarán las solicitudes, pero no realizarán consultas SQL complejas.
- Las vistas del backend serán esquemas de validación y serialización JSON.
- Las rutas actuales se mantendrán temporalmente cuando sea necesario.
- Cada etapa deberá finalizar con sus pruebas aprobadas.
- El contrato HTTP se congelará después de completar y validar el backend.

---

## 1. Reorganización MVC

```text
backend/app/
├── models/
│   ├── user.py
│   ├── registration_request.py
│   ├── productive_unit.py
│   ├── productive_sector.py
│   ├── unit_sector.py
│   ├── product.py
│   ├── product_image.py
│   ├── fair.py
│   ├── fair_participation.py
│   ├── audit.py
│   ├── enums.py
│   └── __init__.py
├── views/
│   ├── auth_view.py
│   ├── registration_request_view.py
│   ├── productive_unit_view.py
│   ├── productive_sector_view.py
│   ├── product_view.py
│   ├── product_image_view.py
│   ├── fair_view.py
│   ├── fair_participation_view.py
│   ├── public_view.py
│   └── error_view.py
├── controllers/
│   ├── auth_controller.py
│   ├── registration_controller.py
│   ├── admin_controller.py
│   ├── productive_unit_controller.py
│   ├── productive_sector_controller.py
│   ├── product_controller.py
│   ├── fair_controller.py
│   └── public_controller.py
├── config.py
├── extensions.py
├── commands.py
├── mail.py
└── __init__.py
```

### Responsabilidades

- Models: entidades SQLAlchemy, relaciones, restricciones, estados, consultas reutilizables y reglas de negocio.
- Views: esquemas Marshmallow, validación de entrada, normalización y serialización uniforme de JSON.
- Controllers: rutas Flask, autenticación, autorización, coordinación de transacciones y respuestas HTTP.

### Reglas del refactor

- No modificar inicialmente el comportamiento funcional.
- Mantener temporalmente las rutas HTTP existentes.
- Eliminar api.py gradualmente después de migrar todas sus rutas.
- Registrar cada grupo de rutas mediante blueprints.
- Mantener las importaciones públicas desde app.models mediante models/__init__.py.
- No crear una carpeta services.
- No modificar React durante esta etapa.
- Separar el refactor estructural de las nuevas funcionalidades.
- Ejecutar todas las pruebas después del refactor.

### Criterios de finalización

- Todas las rutas están distribuidas en controladores.
- Todos los esquemas están en views.
- Todos los modelos están separados por entidad.
- api.py ya no contiene rutas activas.
- Los blueprints se registran correctamente.
- Las migraciones y pruebas actuales funcionan.
- La API mantiene el mismo comportamiento visible.

---

## 2. Migración de nombres y entidades

### Cambios principales

- Exhibitor será reemplazado por ProductiveUnit.
- FairExhibitor será reemplazado por FairParticipation.
- exhibitor_id será reemplazado por productive_unit_id.
- Category será reemplazado por ProductiveSector únicamente cuando represente el rubro de una Unidad Productiva.
- El usuario asociado se representará mediante el rol PRODUCTIVE_UNIT_RESPONSIBLE.

### Nuevas entidades

- RegistrationRequest.
- ProductiveUnit.
- ProductiveSector.
- UnitSector.
- FairParticipation.
- ProductImage, si todavía no existe de forma separada.

No se crearán RedSocial, FairProduct ni ninguna tabla intermedia entre FairParticipation y Product.

### Tratamiento de Category

ProductiveSector clasificará Unidades Productivas, no productos.

La relación correcta será:

ProductiveUnit → UnitSector → ProductiveSector

Si Category clasifica productos, deberá mantenerse temporalmente hasta migrar el backend y retirar la relación Product-Category. Si ya representa rubros de expositores, podrá migrarse conservando sus registros.

### Estrategia de migración

1. Crear nuevas tablas y columnas sin eliminar las anteriores.
2. Añadir claves foráneas, índices y restricciones.
3. Copiar o transformar los datos existentes.
4. Validar cantidades y relaciones migradas.
5. Actualizar modelos, esquemas, controladores y pruebas.
6. Mantener alias temporales de compatibilidad.
7. Eliminar nombres o tablas anteriores en una migración posterior.

### Restricciones e índices mínimos

- Correo único en User.
- Índice para RegistrationRequest.correo_electronico.
- Una sola solicitud PENDING por correo.
- NIT único cuando no sea NULL.
- Correo único en ProductiveUnit.
- UnitSector único por productive_unit_id y productive_sector_id.
- FairParticipation única por fair_id y productive_unit_id.
- Índices sobre estados, fechas de feria, Product.productive_unit_id y ProductImage.product_id.

### Compatibilidad temporal

Las rutas antiguas con exhibitor o category podrán mantenerse como alias, reutilizando la misma lógica y marcándose como obsoletas.

---

## 3. Usuarios, roles y autenticación

El sistema mantendrá una sola entidad User.

No se creará una tabla separada para el Responsable de Unidad Productiva. Se representará mediante User con rol PRODUCTIVE_UNIT_RESPONSIBLE y una relación uno a uno con ProductiveUnit.

### Roles

- ADMIN.
- PRODUCTIVE_UNIT_RESPONSIBLE.

### Atributos mínimos de User

- id.
- nombres.
- apellidos, nullable.
- correo.
- telefono, nullable.
- password_hash.
- role.
- estado.
- cambio_password_obligatorio.
- intentos_fallidos.
- bloqueado_hasta, nullable.
- ultimo_acceso, nullable.
- fecha_creacion.
- fecha_actualizacion.
- deleted_at, nullable.

### Estados

- ACTIVE.
- INACTIVE.
- BLOCKED.

### Reglas

- Normalizar el correo a minúsculas.
- Almacenar contraseñas únicamente como hash.
- Impedir acceso a usuarios eliminados, inactivos o bloqueados.
- Permitir cambios de rol o estado solamente a ADMIN.
- Restringir al responsable a su propia Unidad Productiva y productos.
- Auditar cambios de estado y bloqueos.

### Credenciales temporales

Al aprobar una solicitud:

1. Crear User.
2. Generar contraseña temporal segura.
3. Guardar solo el hash.
4. Establecer cambio_password_obligatorio en true.
5. Enviar credenciales por correo.
6. Restringir el acceso hasta cambiar la contraseña.

Mientras cambio_password_obligatorio sea true, solo se permitirá consultar la sesión, cambiar contraseña y cerrar sesión.

### Intentos fallidos

- Incrementar intentos_fallidos por contraseña incorrecta.
- Bloquear temporalmente al alcanzar el límite.
- Reiniciar el contador después de un acceso correcto.
- Permitir desbloqueo administrativo.
- Configurar límite y duración mediante variables de entorno.

Valores iniciales recomendados: cinco intentos y quince minutos.

### JWT

- Token de acceso.
- Token de actualización.
- Revocación de tokens.
- Validación de expiración y estado del usuario.
- Revocar sesiones al cerrar sesión, cambiar contraseña, bloquear o desactivar una cuenta.

### Recuperación de contraseña

- Generar token aleatorio temporal.
- Guardar únicamente su hash.
- Enviar enlace mediante Brevo.
- Responder de forma uniforme exista o no el correo.
- Invalidar tokens usados, vencidos o anteriores.
- Revocar sesiones después del restablecimiento.

### Endpoints

- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/refresh
- GET /api/auth/me
- POST /api/auth/change-password
- POST /api/auth/forgot-password
- POST /api/auth/reset-password

---

## 4. Solicitud pública de registro

RegistrationRequest representará el formulario enviado antes de crear una cuenta.

El formulario será público y no requerirá autenticación.

### Estados

- PENDING.
- APPROVED.
- REJECTED.

APPROVED y REJECTED serán terminales.

### Atributos mínimos

- id.
- nombre_comercial.
- razon_social.
- nit, nullable.
- registro_seprec, nullable.
- registro_pro_bolivia, nullable.
- nombre_representante.
- departamento.
- direccion_fisica.
- telefono_whatsapp.
- correo_electronico.
- facebook_url, nullable.
- instagram_url, nullable.
- tiktok_url, nullable.
- resena_comercial.
- logo_url, nullable.
- estado.
- fecha_solicitud.
- fecha_revision, nullable.
- observaciones, nullable.
- motivo_rechazo, nullable.
- reviewed_by, nullable.
- credentials_sent_at, nullable.
- notification_status, nullable.
- fecha_actualizacion.

### Campos obligatorios

- Nombre comercial.
- Razón social.
- Nombre del representante.
- Departamento.
- Dirección física.
- Teléfono o WhatsApp.
- Correo electrónico.
- Al menos un Sector Productivo.
- Reseña comercial.

NIT, SEPREC, PRO-BOLIVIA, redes sociales y logotipo serán opcionales.

### Sectores en la solicitud

Se utilizará una tabla intermedia, por ejemplo registration_request_sectors, con:

- registration_request_id.
- productive_sector_id.
- detalle_otro, nullable.

Reglas:

- Al menos un sector.
- Sin duplicados.
- detalle_otro obligatorio cuando se seleccione Otros.
- Solo sectores activos.
- Copiar asociaciones a UnitSector al aprobar.

### Validaciones

- Formato de correo, teléfono y URL.
- Longitud máxima de campos.
- Normalización de textos.
- Validación de logotipo.
- No más de una solicitud PENDING por correo.
- No permitir solicitud si ya existe User o ProductiveUnit activa con el correo.
- Validar NIT duplicado cuando sea proporcionado.
- Permitir nueva solicitud corregida después de REJECTED.

### Logotipo de solicitud

- JPG, JPEG, PNG o WebP.
- Validar extensión, MIME y tamaño.
- Guardar en UPLOAD_FOLDER/solicitudes.
- Mover al directorio de la Unidad Productiva al aprobar.
- Limpiar archivos huérfanos o vencidos mediante comando.

### Rechazo

- Solo para solicitudes PENDING.
- Motivo obligatorio.
- Registrar reviewed_by y fecha_revision.
- Notificar al solicitante.
- No crear User ni ProductiveUnit.
- Conservar historial.

### Endpoints

- POST /api/registration-requests
- GET /api/admin/registration-requests
- GET /api/admin/registration-requests/:id
- POST /api/admin/registration-requests/:id/approve
- POST /api/admin/registration-requests/:id/reject

La consulta administrativa admitirá paginación, búsqueda y filtros por estado, departamento y sector.

---

## 5. Aprobación de solicitudes y generación de credenciales

La aprobación deberá ejecutarse de forma transaccional.

### Condiciones previas

- Solicitud existente y PENDING.
- Campos obligatorios completos.
- Al menos un sector activo.
- Correo y NIT sin duplicados.
- Usuario autenticado con rol ADMIN.

### Proceso

1. Bloquear o volver a consultar la solicitud.
2. Confirmar el estado PENDING.
3. Validar duplicados.
4. Crear ProductiveUnit.
5. Crear User con rol PRODUCTIVE_UNIT_RESPONSIBLE.
6. Relacionar User y ProductiveUnit.
7. Copiar sectores a UnitSector.
8. Transferir el logotipo.
9. Generar contraseña temporal.
10. Guardar solamente el hash.
11. Establecer cambio_password_obligatorio en true.
12. Activar la ProductiveUnit.
13. Cambiar la solicitud a APPROVED.
14. Registrar fecha_revision y reviewed_by.
15. Confirmar la transacción.
16. Enviar credenciales mediante Brevo.
17. Registrar resultado y auditoría.

### Reglas

- Una solicitud solo puede generar una ProductiveUnit.
- User y ProductiveUnit tendrán relación uno a uno.
- Un fallo antes del commit revierte toda la operación.
- Un fallo de correo después del commit no elimina la cuenta.
- El administrador podrá reenviar credenciales.
- El reenvío generará una nueva contraseña temporal y revocará tokens anteriores.
- No registrar contraseñas en logs, auditorías ni respuestas JSON.

### Endpoints

- POST /api/admin/registration-requests/:id/approve
- POST /api/admin/registration-requests/:id/resend-credentials

---

## 6. Gestión de Unidades Productivas

ProductiveUnit representará a las Unidades Productivas aprobadas.

### Atributos mínimos

- id.
- user_id.
- registration_request_id.
- nombre_comercial.
- razon_social.
- nit, nullable.
- registro_seprec, nullable.
- registro_pro_bolivia, nullable.
- nombre_representante.
- departamento.
- direccion_fisica.
- telefono_whatsapp.
- correo_electronico.
- facebook_url, nullable.
- instagram_url, nullable.
- tiktok_url, nullable.
- resena_comercial.
- logo_url, nullable.
- estado.
- fecha_aprobacion.
- fecha_creacion.
- fecha_actualizacion.
- deleted_at, nullable.

### Estados

- ACTIVE.
- INACTIVE.
- SUSPENDED.

### Reglas

- Crear solamente desde una RegistrationRequest APPROVED.
- Relación uno a uno con User.
- registration_request_id único.
- El responsable solo modifica su propia Unidad Productiva.
- El administrador puede consultar y gestionar todas.
- NIT, SEPREC y PRO-BOLIVIA son opcionales.
- Redes sociales como atributos; no crear RedSocial.
- Eliminación lógica.
- INACTIVE, SUSPENDED o eliminada no aparece públicamente.
- SUSPENDED no puede crear ni modificar productos.
- Auditar cambios de estado.
- Mantener coherencia entre correo de acceso y correo de la Unidad Productiva.

### Perfil privado

El responsable podrá actualizar datos comerciales, registros opcionales, representante, ubicación, teléfono, reseña, redes sociales, logotipo y sectores.

No podrá cambiar su estado, rol, responsable, participaciones ni datos históricos de aprobación.

### Logotipo

- JPG, JPEG, PNG o WebP.
- Validar extensión, MIME y tamaño.
- Guardar en UPLOAD_FOLDER/unidades_productivas.
- Reemplazar de forma transaccional.
- Impedir borrados fuera del directorio autorizado.

### Endpoints

- GET /api/admin/productive-units
- GET /api/admin/productive-units/:id
- PATCH /api/admin/productive-units/:id
- PATCH /api/admin/productive-units/:id/status
- DELETE /api/admin/productive-units/:id
- POST /api/admin/productive-units/:id/restore
- GET /api/productive-unit/profile
- PATCH /api/productive-unit/profile
- POST /api/productive-unit/logo
- DELETE /api/productive-unit/logo

---

## 7. Sectores Productivos y UnitSector

ProductiveSector representará los rubros de las Unidades Productivas.

Product no se relacionará directamente con ProductiveSector.

### Sectores iniciales

- Textiles y Confecciones.
- Cuero y Calzados.
- Alimentos y Bebidas Procesados.
- Madera y Carpintería.
- Orfebrería y Joyería.
- Cosmética Natural y Cuidado Personal.
- Artesanía Tradicional o Decorativa.
- Otros.

### ProductiveSector

- id.
- nombre.
- descripcion, nullable.
- estado.
- es_otro.
- fecha_creacion.
- fecha_actualizacion.
- deleted_at, nullable.

### UnitSector

- id.
- productive_unit_id.
- productive_sector_id.
- detalle_otro, nullable.
- estado.
- fecha_asignacion.
- fecha_actualizacion.

### Reglas

- Al menos un sector por Unidad Productiva.
- Selección múltiple.
- Combinación única por unidad y sector.
- Solo sectores activos.
- detalle_otro obligatorio únicamente para Otros.
- No eliminar físicamente sectores con asociaciones.
- Desactivar un sector no elimina el historial.
- El responsable no puede crear sectores globales.
- Auditar asignaciones y retiros.

### Endpoints

- GET /api/productive-sectors
- POST /api/admin/productive-sectors
- GET /api/admin/productive-sectors/:id
- PATCH /api/admin/productive-sectors/:id
- PATCH /api/admin/productive-sectors/:id/status
- DELETE /api/admin/productive-sectors/:id
- GET /api/productive-unit/sectors
- PUT /api/productive-unit/sectors

---

## 8. Productos

Product pertenecerá a una única ProductiveUnit.

### Atributos mínimos

- id.
- productive_unit_id.
- nombre_comercial.
- descripcion_tecnica.
- materia_prima.
- dimensiones, nullable.
- colores_disponibles, nullable.
- certificaciones, nullable.
- presentacion_empaque.
- precio_referencia.
- capacidad_produccion_stock.
- estado.
- fecha_registro.
- fecha_actualizacion.
- deleted_at, nullable.

### Estados

- DRAFT.
- AVAILABLE.
- OUT_OF_STOCK.
- RETIRED.

### Reglas de cantidad

- Máximo cinco productos vigentes por Unidad Productiva.
- Durante la carga inicial podrá tener entre cero y cinco.
- Para aparecer en una feria deberá tener al menos tres productos publicables.
- Un producto publicable está AVAILABLE u OUT_OF_STOCK, no está eliminado y tiene exactamente tres imágenes válidas.
- DRAFT, RETIRED o eliminados no cuentan como publicables.
- RETIRED o eliminados no cuentan dentro del máximo de cinco vigentes.
- No permitir crear un sexto producto vigente.

### Validaciones

- nombre_comercial, descripcion_tecnica, materia_prima, presentacion_empaque, precio_referencia y capacidad_produccion_stock obligatorios.
- precio_referencia mayor o igual a cero.
- Propiedad validada por ProductiveUnit.
- No permitir modificaciones desde unidades inactivas, suspendidas o eliminadas.
- Eliminación lógica.
- Invalidar caché ante cambios.

### Publicación automática

No existirá selección manual de productos por feria.

Cuando exista FairParticipation AUTHORIZED en una feria PUBLISHED:

- Mostrar automáticamente todos los productos publicables.
- Añadir automáticamente productos nuevos cuando cumplan reglas.
- Reflejar cambios de precio, descripción, disponibilidad e imágenes.
- Retirar productos que cambien a DRAFT, RETIRED o sean eliminados.
- Ocultar temporalmente toda la Unidad Productiva si queda con menos de tres productos publicables.

### Endpoints

- GET /api/productive-unit/products
- POST /api/productive-unit/products
- GET /api/productive-unit/products/:id
- PATCH /api/productive-unit/products/:id
- DELETE /api/productive-unit/products/:id
- PATCH /api/productive-unit/products/:id/status
- GET /api/admin/products
- GET /api/admin/products/:id
- PATCH /api/admin/products/:id/status

---

## 9. Imágenes de producto

ProductImage gestionará las  uno a tres fotografías requeridas por producto.

### Atributos mínimos

- id.
- product_id.
- url_imagen.
- texto_alternativo.
- orden_visualizacion.
- es_principal.
- fecha_registro.
- fecha_actualizacion.

### Reglas

- Un producto DRAFT puede tener de cero a tres imágenes.
- No permitir una cuarta imagen.
- Una sola imagen principal.
- Orden único dentro del producto.
- Formatos JPG, JPEG, PNG y WebP.
- Validar extensión, MIME y tamaño.
- Guardar en UPLOAD_FOLDER/productos.
- Impedir path traversal y borrados fuera del directorio.
- Eliminar archivo físico al borrar la imagen.
- Un producto debe tener al menos una imágen.
- Reemplazar guardando primero la nueva imagen.
- Invalidar caché y auditar cambios.

### Endpoints

- GET /api/productive-unit/products/:id/images
- POST /api/productive-unit/products/:id/images
- PATCH /api/productive-unit/products/:id/images/:imageId
- DELETE /api/productive-unit/products/:id/images/:imageId
- PATCH /api/productive-unit/products/:id/images/:imageId/main
- PATCH /api/productive-unit/products/:id/images/order

---

## 10. Ferias automáticas

Fair controlará el catálogo público.

### Atributos mínimos

- id.
- nombre.
- descripcion.
- ubicacion.
- fecha_inicio.
- fecha_fin.
- imagen_portada, nullable.
- estado.
- fecha_registro.
- fecha_actualizacion.
- disabled_at, nullable.
- finished_at, nullable.

### Estados

- DRAFT.
- PUBLISHED.
- FINISHED.
- DISABLED.

### Sincronización en America/La_Paz

- DRAFT antes de fecha_inicio.
- PUBLISHED entre fecha_inicio y fecha_fin, inclusive.
- FINISHED después de fecha_fin.
- DISABLED para cancelación definitiva.

### Reglas

- fecha_inicio menor o igual a fecha_fin.
- Fechas inclusivas.
- Rechazar rangos superpuestos entre ferias no terminales.
- Solo una feria PUBLISHED.
- Permitir edición en DRAFT y PUBLISHED.
- FINISHED y DISABLED son inmutables.
- PUBLISHED no regresa a DRAFT.
- No mover el inicio publicado al futuro.
- No reactivar ferias terminales.
- Sincronizar al consultar catálogo, ferias o dashboard.
- Añadir comando flask sync-fairs.
- Cambios idempotentes y auditados.

### Imágenes de feria

- imagen_portada nullable.
- Archivos únicamente desde /api/uploads.
- Guardar en UPLOAD_FOLDER/ferias.
- Impedir borrados fuera del directorio.
- Al finalizar o desactivar, conservar feria y participaciones, eliminar la portada y establecer imagen_portada en NULL.
- Si ya existe FairImage, conservarlo y limpiar sus archivos; no crearlo como requisito nuevo.
- No modificar usuarios, Unidades Productivas, productos ni imágenes de producto.
- Limpiar archivos huérfanos mediante sync-fairs.

### Endpoints

- GET /api/admin/fairs
- POST /api/admin/fairs
- GET /api/admin/fairs/:id
- PATCH /api/admin/fairs/:id
- POST /api/admin/fairs/:id/publish
- POST /api/admin/fairs/:id/disable
- POST /api/admin/fairs/:id/finish
- POST /api/admin/fairs/:id/cover
- DELETE /api/admin/fairs/:id/cover

---

## 11. Participación de Unidades Productivas

FairParticipation asociará una ProductiveUnit completa con una Fair.

No se creará FairProduct.

### Atributos mínimos

- id.
- fair_id.
- productive_unit_id.
- estado.
- observaciones, nullable.
- fecha_registro.
- fecha_actualizacion.
- authorized_at, nullable.
- revoked_at, nullable.

### Estados

- PENDING.
- AUTHORIZED.
- INACTIVE.
- REVOKED.

### Reglas

- Una feria puede tener varias participaciones.
- Una Unidad Productiva puede participar en varias ferias.
- Combinación fair_id y productive_unit_id única.
- La participación corresponde a toda la Unidad Productiva.
- No hay selección manual de productos.
- Solo autorizar ProductiveUnit ACTIVE.
- Para autorizar, debe tener entre tres y cinco productos publicables.
- AUTHORIZED publica automáticamente todos los productos publicables.
- PENDING, INACTIVE y REVOKED no aparecen públicamente.
- Revocar retira inmediatamente toda la Unidad Productiva y sus productos.
- La revocación no elimina historial, productos ni imágenes.
- No modificar participantes en ferias FINISHED o DISABLED.
- Auditar cambios e invalidar caché.

### Validación dinámica

Aunque la participación siga AUTHORIZED, la visibilidad exige:

- Feria PUBLISHED.
- Unidad Productiva ACTIVE.
- Al menos tres productos publicables.
- Exactamente tres imágenes por producto publicable.

Si queda con menos de tres productos:

- No cambiar automáticamente el estado histórico de la participación.
- Ocultarla temporalmente del catálogo.
- Mostrar advertencia en dashboard.
- Reaparecer automáticamente al recuperar el mínimo.

### Endpoints

- GET /api/admin/fairs/:id/participations
- POST /api/admin/fairs/:id/participations
- GET /api/admin/fairs/:id/participations/:participationId
- PATCH /api/admin/fairs/:id/participations/:participationId
- DELETE /api/admin/fairs/:id/participations/:participationId
- POST /api/admin/fairs/:id/participations/:participationId/authorize
- POST /api/admin/fairs/:id/participations/:participationId/revoke

No se crearán endpoints para asociar productos individualmente.

---

## 12. Catálogo público

### Secuencia de consulta

1. Sincronizar estados de ferias.
2. Obtener la feria PUBLISHED.
3. Obtener FairParticipation AUTHORIZED.
4. Obtener ProductiveUnit ACTIVE y no eliminadas.
5. Verificar de tres a cinco productos publicables.
6. Obtener todos sus Product AVAILABLE u OUT_OF_STOCK.
7. Verificar exactamente tres ProductImage por producto.
8. Serializar sectores y redes sociales.
9. Aplicar filtros, ordenamiento, paginación y caché.

### Exclusiones

- Solicitudes PENDING o REJECTED.
- Unidades Productivas INACTIVE, SUSPENDED o eliminadas.
- Participaciones no autorizadas.
- Unidades Productivas con menos de tres productos publicables.
- Productos DRAFT, RETIRED o eliminados.
- Productos sin exactamente tres imágenes.
- Ferias FINISHED o DISABLED.

### Funcionalidades

- Feria activa.
- Listado y perfil de Unidades Productivas.
- Listado y detalle de productos.
- Búsqueda por nombre de Unidad Productiva o producto.
- Filtros por sector, disponibilidad y departamento.
- Ordenamiento y paginación.
- Redes sociales y WhatsApp.

Cuando no exista feria PUBLISHED, devolver una respuesta válida indicando que no existe catálogo activo.

### Endpoints

- GET /api/public/fairs/active
- GET /api/public/productive-units
- GET /api/public/productive-units/:id
- GET /api/public/products
- GET /api/public/products/:id
- POST /api/public/whatsapp

---

## 13. Contacto mediante WhatsApp

### Entrada

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

### Validaciones

- Al menos un elemento.
- quantity entero positivo.
- Resolver duplicados de forma definida.
- Todos los productos de una misma ProductiveUnit.
- Feria PUBLISHED.
- ProductiveUnit ACTIVE.
- FairParticipation AUTHORIZED.
- Unidad Productiva con al menos tres productos publicables.
- Productos AVAILABLE u OUT_OF_STOCK.
- Exactamente tres imágenes por producto.
- Rechazar DRAFT, RETIRED o eliminados.
- Obtener el número desde ProductiveUnit.telefono_whatsapp.
- No validar FairProduct porque no existe.

El endpoint devolverá una URL codificada; no realizará pedidos ni reservará stock.

---

## 14. Correo electrónico mediante Brevo

Brevo se utilizará para:

- Confirmar recepción de solicitud, cuando se habilite.
- Notificar aprobación.
- Enviar credenciales temporales.
- Notificar rechazo y motivo.
- Reenviar credenciales.
- Recuperar y restablecer contraseña.

### Reglas

- Configuración mediante variables de entorno.
- No incluir claves en el repositorio.
- Plantillas con contenido institucional y variables separadas.
- Registrar fecha, tipo y resultado.
- Los errores no dejan transacciones incompletas.
- Fallos visibles al administrador y reintentos controlados.
- No enviar contraseñas permanentes.
- No registrar tokens completos ni secretos.

Estados sugeridos: PENDING, SENT y FAILED.

---

## 15. Caché e invalidación

### Datos susceptibles de caché

- Feria activa.
- Listado y perfil público de Unidades Productivas.
- Listado y detalle de productos.
- Sectores activos.

### Invalidación

Invalidar al cambiar:

- Ferias.
- Participaciones.
- Unidades Productivas.
- Sectores asignados.
- Productos.
- Estados, precios y disponibilidad.
- Imágenes y logotipos.
- Sincronización automática de ferias.

### Reglas

- La caché no es fuente de verdad.
- Las operaciones administrativas consultan la base de datos.
- Las claves incluyen filtros y paginación.
- Las funciones de invalidación serán reutilizables sin crear services.
- Un fallo de caché no impide consultar la base de datos.

---

## 16. Auditoría

### Atributos mínimos de Audit

- id.
- user_id, nullable.
- accion.
- entidad.
- entidad_id, nullable.
- valores_anteriores, nullable.
- valores_nuevos, nullable.
- direccion_ip, nullable.
- user_agent, nullable.
- fecha_hora.
- resultado.
- detalle, nullable.

### Eventos mínimos

- Solicitudes, aprobaciones y rechazos.
- Creación de User y ProductiveUnit.
- Envío y reenvío de credenciales.
- Cambios de estados.
- Sectores.
- Productos e imágenes.
- Ferias y participaciones.
- Limpieza de archivos.
- Recuperación y cambio de contraseña.
- Bloqueos e intentos fallidos.

### Reglas

- No almacenar contraseñas, tokens completos ni claves.
- Filtrar datos sensibles.
- Conservar auditorías aunque se eliminen lógicamente las entidades.
- Consulta exclusiva para ADMIN.

### Endpoints

- GET /api/admin/audits
- GET /api/admin/audits/:id

---

## 17. Endpoints consolidados

### Estado

- GET /api/health

### Autenticación

- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/refresh
- GET /api/auth/me
- POST /api/auth/change-password
- POST /api/auth/forgot-password
- POST /api/auth/reset-password

### Solicitudes

- POST /api/registration-requests
- GET /api/admin/registration-requests
- GET /api/admin/registration-requests/:id
- POST /api/admin/registration-requests/:id/approve
- POST /api/admin/registration-requests/:id/reject
- POST /api/admin/registration-requests/:id/resend-credentials

### Usuarios

- GET /api/admin/users
- GET /api/admin/users/:id
- PATCH /api/admin/users/:id
- PATCH /api/admin/users/:id/status
- DELETE /api/admin/users/:id
- POST /api/admin/users/:id/restore
- POST /api/admin/users/:id/unlock

### Unidades Productivas

- GET /api/admin/productive-units
- GET /api/admin/productive-units/:id
- PATCH /api/admin/productive-units/:id
- PATCH /api/admin/productive-units/:id/status
- DELETE /api/admin/productive-units/:id
- POST /api/admin/productive-units/:id/restore
- GET /api/productive-unit/profile
- PATCH /api/productive-unit/profile
- POST /api/productive-unit/logo
- DELETE /api/productive-unit/logo

### Sectores

- GET /api/productive-sectors
- POST /api/admin/productive-sectors
- GET /api/admin/productive-sectors/:id
- PATCH /api/admin/productive-sectors/:id
- PATCH /api/admin/productive-sectors/:id/status
- DELETE /api/admin/productive-sectors/:id
- GET /api/productive-unit/sectors
- PUT /api/productive-unit/sectors

### Productos

- GET /api/productive-unit/products
- POST /api/productive-unit/products
- GET /api/productive-unit/products/:id
- PATCH /api/productive-unit/products/:id
- PATCH /api/productive-unit/products/:id/status
- DELETE /api/productive-unit/products/:id
- GET /api/admin/products
- GET /api/admin/products/:id
- PATCH /api/admin/products/:id/status

### Imágenes de producto

- GET /api/productive-unit/products/:id/images
- POST /api/productive-unit/products/:id/images
- PATCH /api/productive-unit/products/:id/images/:imageId
- DELETE /api/productive-unit/products/:id/images/:imageId
- PATCH /api/productive-unit/products/:id/images/:imageId/main
- PATCH /api/productive-unit/products/:id/images/order

### Ferias

- GET /api/admin/fairs
- POST /api/admin/fairs
- GET /api/admin/fairs/:id
- PATCH /api/admin/fairs/:id
- POST /api/admin/fairs/:id/publish
- POST /api/admin/fairs/:id/disable
- POST /api/admin/fairs/:id/finish
- POST /api/admin/fairs/:id/cover
- DELETE /api/admin/fairs/:id/cover

### Participaciones

- GET /api/admin/fairs/:id/participations
- POST /api/admin/fairs/:id/participations
- GET /api/admin/fairs/:id/participations/:participationId
- PATCH /api/admin/fairs/:id/participations/:participationId
- DELETE /api/admin/fairs/:id/participations/:participationId
- POST /api/admin/fairs/:id/participations/:participationId/authorize
- POST /api/admin/fairs/:id/participations/:participationId/revoke

No se crearán endpoints para productos por participación.

### Catálogo público

- GET /api/public/fairs/active
- GET /api/public/productive-units
- GET /api/public/productive-units/:id
- GET /api/public/products
- GET /api/public/products/:id
- POST /api/public/whatsapp

### Auditoría

- GET /api/admin/audits
- GET /api/admin/audits/:id

---

## 18. Pruebas automáticas

Se mantendrán pruebas rápidas con SQLite para reglas aisladas y se ejecutarán migraciones desde cero sobre una base PostgreSQL separada cuyo nombre termine en _test.

### Cobertura mínima

- MVC, blueprints, importaciones y migraciones.
- Roles, propiedad, JWT, revocación, recuperación y bloqueos.
- Solicitudes, duplicados, sectores, aprobación, rechazo y concurrencia.
- Relación User-ProductiveUnit.
- Estados, perfil, logotipo y eliminación lógica.
- UnitSector, Otros y sectores inactivos.
- Máximo cinco productos y mínimo tres publicables.
- Exactamente tres imágenes, portada, orden y borrado seguro.
- Fechas inclusivas, zona America/La_Paz, solapamientos y estados terminales.
- FairParticipation única, autorización, revocación y publicación automática de todos los productos.
- Ocultamiento al perder el mínimo y reaparición al recuperarlo.
- Catálogo, filtros, paginación, WhatsApp y caché.
- Auditoría y protección de archivos.

### Protección de comandos

Los comandos destructivos deberán verificar el entorno y rechazar bases que no terminen en _test durante pruebas destructivas.

---

## 19. Flujo de pruebas de integración

1. Verificar estado de la API.
2. Consultar sectores.
3. Enviar solicitud pública.
4. Consultar y rechazar una solicitud con motivo.
5. Enviar una solicitud corregida.
6. Aprobarla.
7. Crear User y ProductiveUnit transaccionalmente.
8. Copiar sectores.
9. Enviar credenciales.
10. Iniciar sesión con contraseña temporal.
11. Bloquear funcionalidades hasta cambiarla.
12. Actualizar perfil y logotipo.
13. Registrar tres productos.
14. Cargar tres imágenes por producto.
15. Publicar productos.
16. Crear feria y portada.
17. Asignar la Unidad Productiva.
18. Autorizar la participación.
19. Publicar la feria.
20. Verificar que aparecen automáticamente todos sus productos publicables.
21. Editar precio y disponibilidad y verificar el reflejo público.
22. Añadir un cuarto o quinto producto y verificar aparición automática.
23. Rechazar un sexto producto vigente.
24. Generar consulta WhatsApp.
25. Revocar y verificar desaparición inmediata.
26. Reautorizar mientras la feria no sea terminal.
27. Retirar un producto y ocultar la Unidad Productiva si queda con menos de tres publicables.
28. Recuperar el mínimo y verificar reaparición.
29. Finalizar la feria.
30. Verificar desaparición del catálogo.
31. Conservar historial, productos e imágenes de producto.
32. Eliminar de forma segura las imágenes propias de la feria.
33. Ejecutar casos negativos de permisos, propiedad, fechas y validación.

---

## 20. Orden de implementación

### Fase 1. Refactor MVC

- Crear estructura MVC.
- Mover modelos, esquemas y controladores.
- Registrar blueprints.
- Mantener comportamiento y rutas.
- Eliminar api.py después de migrar todo.
- Ejecutar pruebas existentes.

### Fase 2. Migración del dominio

- Migrar Exhibitor a ProductiveUnit.
- Migrar FairExhibitor a FairParticipation.
- Crear ProductiveSector y UnitSector.
- Retirar la relación Product-Category.
- Crear migraciones e índices.
- Mantener alias temporales.

### Fase 3. Solicitudes y aprobación

- Crear RegistrationRequest.
- Implementar formulario, revisión, aprobación y rechazo.
- Crear User y ProductiveUnit transaccionalmente.
- Integrar credenciales temporales, Brevo y auditoría.

### Fase 4. Perfil y sectores

- Completar ProductiveUnit.
- Añadir redes sociales como atributos.
- Completar UnitSector y Otros.
- Implementar perfil y logotipo.

### Fase 5. Productos e imágenes

- Actualizar Product.
- Implementar máximo cinco y mínimo tres publicables.
- Completar ProductImage.
- Exigir tres imágenes.
- Implementar orden, portada y borrado seguro.

### Fase 6. Ferias y participación

- Completar Fair y estados automáticos.
- Completar FairParticipation.
- Autorizar Unidades Productivas completas.
- Derivar automáticamente todos sus productos.
- Implementar revocación, limpieza de imágenes y sync-fairs.

### Fase 7. Catálogo público

- Implementar feria activa, perfiles y productos derivados.
- Añadir búsqueda, filtros, ordenamiento y paginación.
- Actualizar WhatsApp.
- Añadir caché e invalidación.

### Fase 8. Seguridad y cierre

- Completar JWT, recuperación, bloqueos y auditoría.
- Ejecutar pruebas PostgreSQL.
- Generar documentación OpenAPI o equivalente.
- Congelar el contrato HTTP.
- Adaptar React después de aprobar el backend.

Cada fase deberá finalizar con pruebas aprobadas.

---

## 21. Supuestos fijados

- MVC será explícito y estricto.
- No se añadirá services.
- Las reglas de negocio estarán principalmente en modelos.
- Los controladores no realizarán consultas SQL complejas.
- Las vistas serán esquemas y serializadores JSON.
- No se creará RedSocial.
- Facebook, Instagram y TikTok serán atributos de RegistrationRequest y ProductiveUnit.
- No se creará FairProduct.
- FairParticipation relacionará la feria con la Unidad Productiva completa.
- Todos los productos publicables se mostrarán automáticamente.
- No habrá selección manual de productos por feria.
- ProductiveSector clasificará Unidades Productivas, no productos.
- ProductiveUnit se creará solo después de aprobar una solicitud.
- Las credenciales serán temporales y deberán cambiarse en el primer acceso.
- Una Unidad Productiva podrá tener como máximo cinco productos vigentes.
- Para aparecer en el catálogo deberá tener al menos tres productos publicables.
- Cada producto necesitará exactamente tres imágenes para publicarse.
- AVAILABLE y OUT_OF_STOCK serán publicables.
- DRAFT, RETIRED o eliminados no serán públicos.
- Si la Unidad Productiva queda con menos de tres productos publicables, se ocultará temporalmente sin borrar la participación.
- Las ferias históricas conservarán registros y participaciones.
- Las imágenes propias de ferias se eliminarán al finalizar o desactivar definitivamente.
- Las imágenes de productos no se eliminarán al finalizar una feria.
- Inicio y fin serán fechas inclusivas en America/La_Paz.
- FINISHED y DISABLED serán inmutables.
- Las eliminaciones de usuarios, Unidades Productivas y productos serán lógicas.
- El frontend queda fuera de esta etapa.
- El contrato HTTP se congelará después de completar y probar el backend.