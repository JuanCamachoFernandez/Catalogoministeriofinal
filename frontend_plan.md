# Plan de actualización y finalización del frontend

## Resumen

El frontend React/TypeScript se actualizará después de completar, probar y congelar el contrato HTTP del backend definido en `backend_plan.md` y `docs/API.md`.

El trabajo no consistirá únicamente en renombrar pantallas. Se deberá adaptar la aplicación al nuevo flujo institucional:

1. Una persona solicita públicamente el registro de su Unidad Productiva.
2. El administrador revisa, aprueba o rechaza la solicitud.
3. Cuando la solicitud es aprobada, el backend crea la Unidad Productiva y la cuenta de acceso.
4. El responsable recibe credenciales temporales por correo electrónico.
5. El responsable cambia su contraseña y completa su perfil.
6. Registra hasta cinco productos y carga de cero a tres imágenes por producto.
7. El administrador relaciona la Unidad Productiva completa con una feria mediante `FairParticipation`.
8. Todos los productos publicables de la Unidad Productiva autorizada aparecen automáticamente en la feria activa.

No se creará una interfaz para seleccionar productos individualmente por feria porque no existirá `FairProduct`.

## Regla principal del catálogo por ferias

La feria se relacionará con la Unidad Productiva completa mediante `FairParticipation`.

La consulta pública seguirá la relación:

```text
Fair → FairParticipation → ProductiveUnit → Product
```

Cuando una Unidad Productiva tenga una participación `AUTHORIZED` en una feria `PUBLISHED`, el frontend mostrará automáticamente todos sus productos publicables.

Un producto será publicable cuando:

- Tenga estado `AVAILABLE` u `OUT_OF_STOCK`.
- No esté eliminado.
- Tenga al menos 1 hasta tres imágenes válidas.

La Unidad Productiva deberá contar con un mínimo de tres y un máximo de cinco productos publicables para aparecer en el catálogo.

Si durante una feria activa queda con menos de tres productos publicables, se ocultará temporalmente del catálogo, aunque su participación continúe registrada como `AUTHORIZED`.

## Terminología de interfaz y código

Todo el código nuevo y los textos visibles utilizarán la siguiente terminología:

- `ProductiveUnit`: Unidad Productiva.
- `RegistrationRequest`: Solicitud de Registro.
- `ProductiveSector`: Sector Productivo.
- `UnitSector`: asociación de una Unidad Productiva con un Sector Productivo.
- `FairParticipation`: Participación en Feria.
- `Product`: Producto.
- `ProductImage`: Imagen de Producto.

Se reemplazarán progresivamente los términos anteriores:

- Expositor por Unidad Productiva.
- Empresa o emprendimiento por Unidad Productiva cuando representen la entidad principal.
- Categoría por Sector Productivo cuando se refiera al rubro de la Unidad Productiva.
- Portal del expositor por Portal de la Unidad Productiva.
- `FairExhibitor` por `FairParticipation`.

No se creará una pantalla ni recurso independiente para redes sociales. Facebook, Instagram y TikTok serán campos opcionales del formulario de solicitud y del perfil de la Unidad Productiva.

---

## 1. Estado base e impacto del nuevo contrato

El frontend existente puede conservar como línea base:

- React, TypeScript y Vite.
- React Router.
- TanStack Query.
- React Hook Form y Zod.
- Axios.
- Componentes comunes.
- Diseño responsivo y tema institucional.
- Pruebas unitarias, de componentes y E2E existentes.

Sin embargo, las verificaciones y cantidades de pruebas registradas en el plan anterior deberán considerarse históricas. Después de cambiar el dominio y los endpoints, deberán ejecutarse nuevamente `lint`, TypeScript, pruebas y build.

### Elementos que deberán cambiar

- El registro directo de expositores será reemplazado por solicitudes públicas.
- El administrador ya no creará Unidades Productivas manualmente desde un formulario normal.
- Se añadirá revisión, aprobación, rechazo y reenvío de credenciales.
- `Exhibitor` será reemplazado por `ProductiveUnit`.
- `Category` será reemplazado por `ProductiveSector` cuando represente rubros.
- Los productos dejarán de depender de categorías o sectores.
- La clasificación múltiple corresponderá a la Unidad Productiva.
- Cada Unidad Productiva podrá tener hasta cinco productos vigentes.
- Para aparecer en catálogo deberá tener al menos tres productos publicables.
- Cada producto necesitará al menos una hasta tres imágenes para publicarse.
- La asignación a ferias se realizará por Unidad Productiva completa.
- No habrá selección individual de productos por feria.
- Los roles visibles serán `ADMIN` y `PRODUCTIVE_UNIT_RESPONSIBLE`.
- Se añadirá el cambio obligatorio de contraseña temporal.
- Se actualizarán todas las rutas, servicios, tipos, claves de consulta y textos.

### Fuente de verdad

Después de finalizar el backend, el orden de prioridad será:

1. Contrato ejecutable del backend.
2. `docs/API.md` u OpenAPI generado.
3. `backend_plan.md`.
4. Este plan del frontend.
5. Propuesta institucional.

Cuando exista una diferencia, no se deberá inventar un comportamiento en el frontend. Se deberá adaptar la interfaz al contrato final del backend.

---

## 2. Objetivo

Actualizar y completar el frontend React/TypeScript para ofrecer cuatro experiencias principales:

1. Catálogo público para visitantes.
2. Formulario público de solicitud de registro.
3. Portal administrativo para revisión y gestión institucional.
4. Portal privado para responsables de Unidades Productivas aprobadas.

La aplicación deberá consumir todos los endpoints definidos por el backend, respetar roles, propiedad, estados terminales, validaciones de archivos y reglas automáticas de publicación.

---

## 3. Arquitectura propuesta

La estructura de `frontend/src` se reorganizará gradualmente de la siguiente manera:

```text
src/
├── app/
│   ├── router.tsx
│   ├── providers.tsx
│   ├── queryClient.ts
│   └── config.ts
├── api/
│   ├── client.ts
│   ├── errors.ts
│   ├── pagination.ts
│   ├── queryKeys.ts
│   └── types.ts
├── auth/
│   ├── AuthProvider.tsx
│   ├── guards/
│   ├── pages/
│   └── api/
├── components/
│   ├── forms/
│   ├── feedback/
│   ├── navigation/
│   ├── tables/
│   ├── images/
│   └── modals/
├── layouts/
│   ├── PublicLayout.tsx
│   ├── AdminLayout.tsx
│   └── ProductiveUnitLayout.tsx
├── features/
│   ├── registration-requests/
│   ├── productive-units/
│   ├── productive-sectors/
│   ├── products/
│   ├── product-images/
│   ├── fairs/
│   ├── fair-participations/
│   ├── catalog/
│   ├── whatsapp/
│   ├── users/
│   ├── audit/
│   └── dashboard/
├── hooks/
├── styles/
├── utils/
└── test/
```

### Reglas técnicas

- Evitar `any`; todas las respuestas y formularios deberán tener tipos TypeScript.
- Definir tipos separados para lectura, creación, actualización, filtros y respuestas paginadas.
- Mantener un módulo API por dominio.
- Centralizar las claves de TanStack Query.
- Utilizar React Hook Form y Zod para formularios.
- Convertir los errores `error/details` del backend en errores de campo.
- No duplicar reglas críticas del backend; las validaciones del frontend serán preventivas y de experiencia de usuario.
- Invalidar solamente las consultas afectadas por cada mutación.
- Resolver la URL del backend y archivos mediante variables de entorno.
- No escribir rutas de archivos arbitrarias en formularios.
- Reutilizar componentes para tablas, paginación, filtros, confirmaciones, carga, error y vacío.
- Mantener etiquetas asociadas, navegación por teclado, foco visible, textos alternativos y modales accesibles.
- Separar los componentes de interfaz de los servicios HTTP.
- No mantener pantallas completas concentradas en un único archivo como `AdminPortal.tsx`.

### Variables de entorno

Documentar como mínimo:

```env
VITE_API_URL=
VITE_PUBLIC_URL=
VITE_APP_NAME=
```

La URL de imágenes deberá construirse desde la respuesta del backend o desde una función centralizada. No se concatenarán rutas manualmente dentro de componentes.

---

## 4. Rutas de la aplicación

### Rutas públicas

- `/`
- `/catalogo`
- `/unidades-productivas`
- `/unidades-productivas/:id`
- `/productos`
- `/productos/:id`
- `/solicitud-registro`
- `/solicitud-registro/enviada`
- `/login`
- `/olvide-contrasena`
- `/restablecer-contrasena`

### Rutas administrativas

- `/admin`
- `/admin/solicitudes`
- `/admin/solicitudes/:id`
- `/admin/unidades-productivas`
- `/admin/unidades-productivas/:id`
- `/admin/sectores-productivos`
- `/admin/productos`
- `/admin/productos/:id`
- `/admin/ferias`
- `/admin/ferias/:id`
- `/admin/ferias/:id/participaciones`
- `/admin/usuarios`
- `/admin/usuarios/:id`
- `/admin/auditoria`

### Rutas de la Unidad Productiva

- `/unidad-productiva`
- `/unidad-productiva/perfil`
- `/unidad-productiva/sectores`
- `/unidad-productiva/productos`
- `/unidad-productiva/productos/nuevo`
- `/unidad-productiva/productos/:id`
- `/unidad-productiva/productos/:id/imagenes`

### Guardas

- Las rutas públicas no requerirán sesión.
- Las rutas administrativas exigirán rol `ADMIN`.
- Las rutas de la Unidad Productiva exigirán rol `PRODUCTIVE_UNIT_RESPONSIBLE`.
- Mientras `cambio_password_obligatorio` sea `true`, solamente se permitirán las rutas de sesión, cambio de contraseña y cierre de sesión.
- Un usuario autenticado no podrá abrir pantallas de otro rol escribiendo la URL directamente.

---

## 5. Fases de ejecución

### Fase 0 — Línea base y contrato congelado

Objetivo: preparar el frontend para consumir el nuevo backend sin mezclar contratos antiguos y nuevos.

Tareas:

- Esperar la finalización y aprobación del backend.
- Revisar `docs/API.md` u OpenAPI.
- Ejecutar `npm run lint`, `npx tsc --noEmit`, `npm test` y `npm run build`.
- Registrar los fallos existentes antes de modificar código.
- Crear o actualizar `docs/MATRIZ_FRONTEND_API.md`.
- Mapear endpoint, pantalla, rol, tipos, estado y pruebas.
- Corregir textos con codificación dañada.
- Identificar todos los usos de `exhibitor`, `category` y `FairExhibitor`.
- Identificar rutas y componentes que deberán conservar alias temporales.
- Tipar las respuestas paginadas y errores comunes.
- Actualizar `.env.example`.

Criterio de aceptación:

- El contrato final está documentado.
- La línea base compila o sus fallos están identificados.
- No existen endpoints ambiguos.
- Se dispone de una matriz completa antes de implementar pantallas.

### Fase 1 — Base transversal, autenticación y navegación

Objetivo: adaptar la sesión y los permisos al nuevo dominio.

Tareas:

- Dividir el router por rutas públicas, administrativas y de Unidad Productiva.
- Implementar `PublicRoute`, `AuthenticatedRoute` y `RoleRoute`.
- Restaurar la sesión con `GET /api/auth/me`.
- Configurar el interceptor Axios para JWT, refresh y normalización de errores.
- Implementar cierre mediante `POST /api/auth/logout` antes de limpiar la sesión local.
- Limpiar solamente las claves de autenticación; no utilizar `localStorage.clear()`.
- Implementar recuperación y restablecimiento de contraseña.
- Implementar cambio obligatorio de contraseña temporal.
- Bloquear el resto del portal hasta completar el cambio.
- Mostrar estados `ACTIVE`, `INACTIVE` y `BLOCKED` de forma comprensible.
- Manejar globalmente respuestas 401 y 403.
- Crear `AdminLayout` y `ProductiveUnitLayout`.
- Ocultar opciones no autorizadas sin depender únicamente de ello para la seguridad.
- Crear notificaciones, confirmaciones y estados comunes.

Criterio de aceptación:

- Login, restauración, refresh, logout, recuperación y cambio funcionan de extremo a extremo.
- Un responsable no puede ingresar a rutas administrativas.
- Un administrador no accede accidentalmente al portal como responsable.
- La contraseña temporal bloquea las funcionalidades privadas hasta ser cambiada.

### Fase 2 — Solicitud pública de registro

Objetivo: permitir que una Unidad Productiva solicite su incorporación sin crear una cuenta directamente.

Tareas:

- Crear el formulario público para `POST /api/registration-requests`.
- No solicitar productos en esta etapa.
- Implementar los siguientes campos:
  - Nombre comercial.
  - Razón social.
  - NIT opcional.
  - Registro SEPREC opcional.
  - Registro PRO-BOLIVIA opcional.
  - Nombre del representante legal o propietario.
  - Departamento.
  - Dirección física de la planta o taller.
  - Teléfono o WhatsApp comercial.
  - Correo electrónico.
  - Facebook opcional.
  - Instagram opcional.
  - TikTok opcional.
  - Uno o varios Sectores Productivos.
  - Detalle obligatorio cuando se seleccione Otros.
  - Reseña comercial.
  - Logotipo opcional.
- Cargar los sectores mediante `GET /api/productive-sectors`.
- Utilizar selector múltiple accesible.
- Validar preventivamente correo, teléfono, URL, longitud y archivos.
- Mostrar los errores específicos del backend.
- Implementar carga del logotipo según el formato final del endpoint.
- Mostrar progreso de archivo y vista previa.
- Evitar envíos repetidos mientras la solicitud esté en curso.
- Mostrar una pantalla de confirmación con identificador, estado y fecha.
- Informar que el envío no crea una cuenta de acceso inmediata.
- Informar que los productos se registrarán después de la aprobación.

Criterio de aceptación:

- Una persona puede enviar una solicitud sin iniciar sesión.
- La selección múltiple de sectores funciona.
- Otros exige detalle.
- Los campos opcionales no bloquean el envío.
- Los duplicados y validaciones se muestran sin perder los datos ingresados.
- No se crea visualmente una cuenta ni un producto desde este flujo.

### Fase 3 — Gestión administrativa de solicitudes

Objetivo: permitir que el administrador revise y resuelva las solicitudes.

Tareas:

- Crear listado paginado de solicitudes.
- Añadir filtros por estado, departamento y Sector Productivo.
- Añadir búsqueda por nombre comercial, razón social, correo y NIT.
- Mostrar estados `PENDING`, `APPROVED` y `REJECTED` con texto e icono.
- Crear vista de detalle con toda la información enviada.
- Mostrar logotipo y enlaces sociales cuando existan.
- Mostrar sectores seleccionados y detalle de Otros.
- Implementar aprobación con confirmación.
- Informar que la aprobación creará `User` y `ProductiveUnit`.
- Mostrar el estado del envío de credenciales devuelto por el backend.
- Implementar rechazo con motivo obligatorio.
- No permitir editar silenciosamente los datos del solicitante.
- Bloquear acciones sobre solicitudes terminales.
- Implementar reenvío de credenciales para solicitudes aprobadas cuando corresponda.
- Mostrar `PENDING`, `SENT` o `FAILED` para notificaciones.
- Mantener accesibles las solicitudes históricas.

Criterio de aceptación:

- El administrador puede localizar y revisar solicitudes.
- Aprobar crea la Unidad Productiva y cuenta según el backend.
- Rechazar exige motivo.
- Las acciones terminales quedan bloqueadas.
- Los fallos de correo se muestran sin afirmar que la aprobación falló.
- El reenvío de credenciales tiene confirmación y estado visible.

### Fase 4 — Gestión de Unidades Productivas y Sectores Productivos

Objetivo: reemplazar las pantallas de expositores y categorías por el nuevo dominio.

#### Unidades Productivas

- Listar con paginación, búsqueda y filtros.
- Filtrar por estado, departamento y sector.
- Mostrar nombre comercial, razón social, representante, contacto y estado.
- Consultar detalle completo.
- Mostrar usuario responsable y solicitud de origen.
- Mostrar sectores, productos y participaciones relacionadas.
- Activar, desactivar, suspender, eliminar lógicamente y restaurar según endpoints.
- Mostrar claramente los efectos de cada estado sobre el acceso y catálogo.
- No ofrecer creación manual de Unidad Productiva si el backend solo permite creación por aprobación.
- No permitir cambiar arbitrariamente el usuario responsable.

#### Sectores Productivos

- Reemplazar las pantallas de categorías.
- Listar sectores activos e inactivos.
- Crear, editar, activar y desactivar.
- Eliminar únicamente cuando el backend lo permita.
- Mostrar `es_otro` de forma clara.
- No relacionar sectores con productos.
- Mostrar la cantidad de Unidades Productivas asociadas cuando el backend la proporcione.

Criterio de aceptación:

- Ya no existen textos funcionales de expositor o categoría en pantallas nuevas.
- La UI no crea Unidades Productivas fuera del flujo de aprobación.
- Los sectores clasifican Unidades Productivas, no productos.
- Estados y errores administrativos se muestran correctamente.

### Fase 5 — Portal de la Unidad Productiva

Objetivo: permitir que el responsable gestione únicamente sus propios datos.

Tareas:

- Crear dashboard privado.
- Consultar perfil mediante `GET /api/productive-unit/profile`.
- Editar mediante `PATCH /api/productive-unit/profile`.
- Mostrar y actualizar Facebook, Instagram y TikTok como campos del perfil.
- Gestionar el logotipo con los endpoints correspondientes.
- Consultar y actualizar sectores con `GET/PUT /api/productive-unit/sectors`.
- Exigir al menos un sector.
- Exigir detalle para Otros.
- Mostrar estado de la Unidad Productiva y cuenta.
- Mostrar resumen de productos:
  - Productos vigentes.
  - Productos publicables.
  - Máximo permitido.
  - Cantidad faltante para alcanzar el mínimo público.
- Mostrar estado de preparación para feria:
  - No lista.
  - Lista con tres a cinco productos publicables.
  - Oculta temporalmente por incumplimiento.
- Mostrar participaciones solamente como información, sin permitir asignarse a una feria.
- Impedir cualquier acceso visual a datos de otra Unidad Productiva.

Criterio de aceptación:

- El responsable modifica únicamente su perfil.
- Las redes sociales son campos, no entidades separadas.
- Los sectores múltiples se guardan correctamente.
- El dashboard explica con claridad el mínimo de tres y máximo de cinco productos.
- No se ofrecen acciones administrativas.

### Fase 6 — Productos e imágenes

Objetivo: adaptar el CRUD de productos a los nuevos campos y reglas de publicación.

#### Formulario de producto

Implementar:

- Nombre comercial.
- Descripción técnica.
- Materia prima.
- Dimensiones opcionales.
- Colores disponibles opcionales.
- Certificaciones opcionales.
- Presentación o empaque.
- Precio de referencia.
- Capacidad de producción mensual o disponibilidad de stock.
- Estado.

Eliminar cualquier selector obligatorio de Categoría o Sector Productivo del formulario del producto.

#### Reglas de cantidad

- Permitir crear productos mientras existan menos de cinco vigentes.
- Deshabilitar el botón de creación al alcanzar cinco.
- Mostrar contador visible, por ejemplo `3 de 5 productos vigentes`.
- Los productos `RETIRED` o eliminados no deberán ocupar el límite cuando así lo confirme el backend.
- No asumir que un producto creado queda publicado automáticamente.

#### Imágenes

- Permitir entre cero y tres imágenes mientras el producto esté `DRAFT`.
- Exigir al menos 1 hasta tres para cambiar a `AVAILABLE` u `OUT_OF_STOCK`.
- No permitir cargar una cuarta imagen.
- Permitir definir imagen principal.
- Permitir cambiar orden.
- Permitir editar texto alternativo.
- Implementar reemplazo seguro.
- Mostrar progreso, vista previa y errores de tipo o tamaño.
- Impedir desde la interfaz eliminar una imagen cuando dejaría un producto publicado con menos de tres, mostrando el error del backend si existe concurrencia.

#### Estados y publicación

- Mostrar `DRAFT`, `AVAILABLE`, `OUT_OF_STOCK` y `RETIRED`.
- Explicar que `AVAILABLE` y `OUT_OF_STOCK` pueden aparecer en catálogo.
- Mostrar un indicador `Publicable` o `No publicable` calculado desde los datos del backend.
- Advertir el efecto inmediato de retirar o eliminar productos durante una feria activa.
- Si la Unidad Productiva queda con menos de tres publicables, mostrar una advertencia de que desaparecerá temporalmente del catálogo.

Criterio de aceptación:

- No se puede crear un sexto producto vigente.
- No se puede publicar un producto con una cantidad de imágenes menos a 1.
- Los campos coinciden con el nuevo modelo.
- No existe selector de sector en producto.
- Los cambios públicos se reflejan después de invalidar las consultas correspondientes.

### Fase 7 — Gestión de ferias y participaciones

Objetivo: alinear la interfaz administrativa con el ciclo automático y la asignación por Unidad Productiva completa.

#### Ferias

- Listar y filtrar ferias.
- Crear feria con nombre, descripción, ubicación, fechas y portada opcional.
- Cargar la portada mediante el endpoint de archivos, no mediante una URL escrita manualmente.
- Validar fecha de inicio y fin.
- Mostrar errores de rangos superpuestos.
- Mostrar estados `DRAFT`, `PUBLISHED`, `FINISHED` y `DISABLED`.
- Editar únicamente `DRAFT` y `PUBLISHED`.
- Bloquear controles en ferias terminales.
- No ofrecer una acción que adelante arbitrariamente la publicación antes de la fecha.
- Si el endpoint `/publish` permanece en el contrato final, utilizarlo únicamente de la forma documentada por el backend y sin contradecir el ciclo automático.
- Permitir finalizar o desactivar solamente cuando el backend lo admita.
- Informar que la portada de una feria finalizada o desactivada será eliminada, pero su historial se conservará.

#### Participaciones

- Crear una participación seleccionando una Unidad Productiva.
- No mostrar selectores de productos.
- Mostrar la cantidad actual de productos publicables de la Unidad Productiva.
- Impedir o advertir la autorización cuando tenga menos de tres o más de cinco productos publicables.
- Mostrar estados `PENDING`, `AUTHORIZED`, `INACTIVE` y `REVOKED`.
- Implementar autorización y revocación con confirmación.
- Explicar que autorizar publica automáticamente todos los productos publicables.
- Explicar que revocar retira toda la Unidad Productiva y sus productos del catálogo.
- Mostrar advertencia cuando una participación autorizada esté oculta temporalmente por tener menos de tres productos publicables.
- Bloquear cambios en ferias `FINISHED` y `DISABLED`.
- Conservar la consulta del historial.

Criterio de aceptación:

- No existe ninguna pantalla ni endpoint visual para elegir productos por feria.
- La participación se asigna únicamente a la Unidad Productiva.
- La autorización muestra automáticamente todos sus productos publicables.
- La revocación los retira en conjunto.
- Los estados terminales bloquean acciones inválidas.

### Fase 8 — Catálogo público y WhatsApp

Objetivo: adaptar la experiencia pública al nuevo modelo institucional.

#### Feria activa

- Consultar `GET /api/public/fairs/active`.
- Mostrar portada, nombre, descripción, ubicación y fechas.
- Mostrar un estado informativo cuando no exista feria activa.
- No mostrar controles administrativos.

#### Unidades Productivas

- Consultar listado paginado.
- Buscar por nombre comercial.
- Filtrar por Sector Productivo y departamento.
- Mostrar logotipo, nombre comercial, reseña, sector, ubicación y contacto disponible.
- Crear perfil público con:
  - Nombre comercial.
  - Razón social cuando corresponda públicamente.
  - Reseña comercial.
  - Sectores.
  - Departamento y dirección pública autorizada.
  - WhatsApp.
  - Facebook, Instagram y TikTok cuando existan.
  - Todos los productos publicables.

#### Productos

- Buscar por nombre comercial.
- Filtrar por disponibilidad.
- Mostrar de una hasta tres imágenes.
- Mostrar nombre, descripción técnica, materia prima, presentación, precio de referencia y capacidad o stock.
- Mostrar claramente `AVAILABLE` y `OUT_OF_STOCK`.
- No mostrar `DRAFT`, `RETIRED` ni eliminados.
- No mostrar Unidades Productivas con menos de tres productos publicables.

#### WhatsApp

Enviar:

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

Reglas de interfaz:

- Capturar cantidades enteras positivas.
- Mantener todos los productos seleccionados dentro de una misma Unidad Productiva.
- Limpiar la selección al cambiar de Unidad Productiva o feria.
- No enviar productos que hayan dejado de ser visibles.
- Permitir consultar productos `AVAILABLE` y `OUT_OF_STOCK` si el contrato final mantiene ambos estados como consultables.
- Mostrar el error del backend cuando el catálogo haya cambiado entre la selección y el envío.
- Abrir la URL devuelta por el backend.
- No representar la consulta como pedido, compra o reserva de stock.

Criterio de aceptación:

- El visitante encuentra una Unidad Productiva y sus productos.
- Todos los productos visibles se derivan automáticamente de la participación.
- Los filtros y paginación funcionan.
- WhatsApp utiliza cantidades y un único propietario.
- La ausencia de feria se muestra correctamente.

### Fase 9 — Usuarios, dashboard y auditoría

Objetivo: completar las herramientas institucionales restantes.

#### Usuarios

- Listar con paginación, búsqueda y filtros.
- Mostrar rol, estado, bloqueo y Unidad Productiva relacionada.
- Editar únicamente los campos permitidos.
- Activar, desactivar, desbloquear, eliminar lógicamente y restaurar.
- No permitir cambiar el rol desde formularios no autorizados.
- Mostrar confirmaciones y efectos de cada acción.

#### Dashboard

Mostrar indicadores como:

- Solicitudes pendientes.
- Solicitudes aprobadas y rechazadas.
- Unidades Productivas activas, inactivas y suspendidas.
- Unidades Productivas listas para feria.
- Participaciones autorizadas pero ocultas por incumplir el mínimo de productos.
- Productos por estado.
- Feria actual y próxima feria.
- Fallos de envío de credenciales.
- Actividad reciente.

#### Auditoría

- Listar con paginación.
- Filtrar por usuario, acción, entidad, resultado y fechas.
- Mostrar detalle sin exponer información sensible.
- No mostrar contraseñas, tokens ni secretos aunque aparezcan accidentalmente en una respuesta antigua.

Criterio de aceptación:

- Las operaciones administrativas relevantes están disponibles.
- Los indicadores permiten encontrar pendientes y errores.
- La auditoría es consultable únicamente por ADMIN.

### Fase 10 — Calidad, rendimiento y entrega

Objetivo: cerrar la implementación y preparar el frontend para producción.

Tareas:

- Pruebas unitarias para validadores, tipos, sesión, cantidades y helpers de publicación.
- Pruebas de componentes para formularios, archivos, tablas, filtros, estados y modales.
- Pruebas integradas con API simulada para solicitudes, aprobación, perfil, productos, ferias y WhatsApp.
- Pruebas E2E de recorridos críticos.
- Auditoría responsiva en móvil, tableta y escritorio.
- Auditoría de accesibilidad y teclado.
- Carga diferida por ruta.
- Optimización de imágenes y skeletons.
- Manejo global de errores inesperados.
- Página 404 y páginas de acceso denegado.
- Verificación en Chrome, Edge, Firefox y Safari/WebKit.
- Actualización de README, manual y capturas.
- Actualización final de `docs/MATRIZ_FRONTEND_API.md`.

Comandos de verificación:

```bash
npm run lint
npx tsc --noEmit
npm test
npm run test:e2e
npm run build
```

Criterio de aceptación:

- Todos los comandos finalizan correctamente.
- Los recorridos críticos están automatizados.
- No existen vulneraciones evidentes de rol o propiedad.
- No existen textos con codificación dañada.
- La aplicación funciona en móvil y escritorio.
- El contrato consumido coincide con el backend congelado.

---

## 6. Servicios API por dominio

Se crearán o actualizarán módulos para:

- `authApi`.
- `registrationRequestsApi`.
- `usersApi`.
- `productiveUnitsApi`.
- `productiveSectorsApi`.
- `productsApi`.
- `productImagesApi`.
- `fairsApi`.
- `fairParticipationsApi`.
- `catalogApi`.
- `whatsappApi`.
- `auditApi`.

No se creará `fairProductsApi`.

Cada módulo deberá:

- Tener tipos de entrada y salida.
- Utilizar el cliente Axios central.
- No acceder directamente a componentes de interfaz.
- Normalizar respuestas paginadas.
- Mantener nombres coherentes con el backend.
- Tener claves de consulta centralizadas.

---

## 7. Matriz mínima de endpoints y pantallas

| Dominio | Endpoint principal | Pantalla |
|---|---|---|
| Autenticación | `POST /api/auth/login` | Inicio de sesión |
| Sesión | `GET /api/auth/me` | Restauración y perfil de sesión |
| Solicitudes | `POST /api/registration-requests` | Formulario público |
| Solicitudes | `GET /api/admin/registration-requests` | Bandeja administrativa |
| Solicitudes | `POST .../:id/approve` | Detalle de solicitud |
| Solicitudes | `POST .../:id/reject` | Detalle de solicitud |
| Unidades Productivas | `GET /api/admin/productive-units` | Gestión administrativa |
| Perfil | `GET/PATCH /api/productive-unit/profile` | Portal privado |
| Sectores | `GET /api/productive-sectors` | Formulario público y filtros |
| Sectores propios | `PUT /api/productive-unit/sectors` | Perfil privado |
| Productos | `GET/POST /api/productive-unit/products` | Productos propios |
| Imágenes | `POST .../products/:id/images` | Galería de producto |
| Ferias | `GET/POST /api/admin/fairs` | Gestión de ferias |
| Participaciones | `GET/POST .../participations` | Participantes de feria |
| Catálogo | `GET /api/public/fairs/active` | Portada pública |
| Catálogo | `GET /api/public/productive-units` | Listado público |
| Catálogo | `GET /api/public/products` | Listado público de productos |
| WhatsApp | `POST /api/public/whatsapp` | Consulta de productos |
| Auditoría | `GET /api/admin/audits` | Auditoría administrativa |

La matriz completa deberá mantenerse en `docs/MATRIZ_FRONTEND_API.md`.

---

## 8. Orden recomendado de entregas

| Entrega | Alcance demostrable | Prioridad |
|---|---|---|
| E1 | Contrato, tipos, sesión, guardas, errores y layouts | Crítica |
| E2 | Solicitud pública y bandeja administrativa | Crítica |
| E3 | Aprobación, credenciales, Unidades Productivas y sectores | Crítica |
| E4 | Portal privado, productos y exactamente tres imágenes | Alta |
| E5 | Ferias y participaciones por Unidad Productiva completa | Alta |
| E6 | Catálogo público, filtros, cantidades y WhatsApp | Alta |
| E7 | Usuarios, dashboard, auditoría y calidad final | Media/alta |

Cada entrega deberá incluir:

- Funcionalidad completa.
- Estados de carga, éxito, vacío y error.
- Validación.
- Control de permisos.
- Pruebas proporcionales al riesgo.
- Actualización de documentación.

---

## 9. Casos de aceptación finales

1. Una persona completa una solicitud pública sin crear una cuenta inmediatamente.
2. La solicitud admite varios Sectores Productivos y exige detalle para Otros.
3. El administrador revisa la solicitud y la rechaza con motivo obligatorio.
4. Una nueva solicitud corregida puede enviarse después del rechazo.
5. El administrador aprueba una solicitud y visualiza el resultado del envío de credenciales.
6. El responsable inicia sesión con contraseña temporal y debe cambiarla antes de entrar al portal.
7. El responsable actualiza únicamente su Unidad Productiva.
8. Facebook, Instagram y TikTok se administran como campos del perfil.
9. La Unidad Productiva registra hasta cinco productos.
10. Un producto no puede publicarse sin al menos una hasta tres imágenes.
11. El formulario de producto no solicita Sector Productivo.
12. El administrador crea una feria futura sin activarla anticipadamente.
13. El administrador asigna una Unidad Productiva completa a la feria.
14. La interfaz no permite seleccionar productos individuales por feria.
15. La participación solo se autoriza cuando existen al menos tres productos publicables.
16. Al publicarse la feria, aparecen automáticamente todos los productos publicables de la Unidad Productiva.
17. Un producto nuevo aparece automáticamente cuando queda publicable.
18. Cambiar precio, descripción o disponibilidad se refleja en el catálogo.
19. Retirar un producto lo elimina del catálogo sin modificar la participación.
20. Si la Unidad Productiva queda con menos de tres productos publicables, desaparece temporalmente del catálogo.
21. Al recuperar el mínimo, reaparece automáticamente.
22. Revocar la participación retira toda la Unidad Productiva y sus productos.
23. Un visitante filtra por sector y departamento.
24. Un visitante selecciona cantidades de productos pertenecientes a una sola Unidad Productiva.
25. WhatsApp abre la URL generada por el backend.
26. Al finalizar o desactivar la feria, el catálogo deja de mostrarla.
27. Las imágenes de productos se conservan aunque la feria termine.
28. Las operaciones terminales quedan bloqueadas en la interfaz.
29. Los flujos críticos funcionan en móvil y escritorio.
30. Las pruebas, lint, TypeScript y build finalizan correctamente.

---

## 10. Definición de terminado

Una tarea se considerará terminada cuando:

- Consume el endpoint y formato definidos por el backend congelado.
- Utiliza la terminología nueva.
- Respeta rol, propiedad y estados.
- Incluye estados de carga, éxito, vacío, validación y error.
- No introduce `any` sin justificación.
- No duplica reglas críticas de negocio de forma divergente.
- Tiene pruebas proporcionales al riesgo.
- Invalida correctamente las consultas afectadas.
- Funciona con teclado y en vista móvil.
- No contiene textos con codificación incorrecta.
- Pasa lint, TypeScript, pruebas y build.
- Actualiza la matriz de endpoints y la documentación correspondiente.

---

## 11. Supuestos fijados

- El frontend se adaptará después de congelar el contrato del backend.
- Los roles serán `ADMIN` y `PRODUCTIVE_UNIT_RESPONSIBLE`.
- No habrá registro público directo de usuarios.
- Una solicitud aprobada generará la cuenta y la Unidad Productiva.
- No se creará una interfaz para RedSocial.
- Facebook, Instagram y TikTok serán campos de solicitud y perfil.
- ProductiveSector clasificará Unidades Productivas, no productos.
- No se creará `FairProduct` ni una pantalla para seleccionar productos por feria.
- La participación se asignará a la Unidad Productiva completa.
- Todos sus productos publicables aparecerán automáticamente.
- Una Unidad Productiva podrá tener como máximo cinco productos vigentes.
- Para mostrarse públicamente deberá tener al menos tres productos publicables.
- Cada producto necesitará al menos una hasta tres imágenes para publicarse.
- Los productos `AVAILABLE` y `OUT_OF_STOCK` serán visibles cuando cumplan las demás reglas.
- Los productos `DRAFT`, `RETIRED` o eliminados no serán públicos.
- Una participación autorizada podrá quedar temporalmente oculta sin perder su estado histórico.
- Las fechas de feria se interpretarán en `America/La_Paz` y serán inclusivas.
- Las ferias `FINISHED` y `DISABLED` serán inmutables.
- El frontend no adelantará manualmente una feria antes de su fecha.
- Las eliminaciones lógicas se representarán sin ocultar el historial administrativo.
- El frontend no almacenará secretos ni contraseñas temporales.
- Las rutas antiguas podrán mantenerse temporalmente como compatibilidad, pero las nuevas funcionalidades usarán los nombres actualizados.