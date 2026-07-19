# Plan de mejora y finalización del frontend

## Estado de implementación

Implementado en julio de 2026:

- Base tipada, sesión restaurable, cierre revocado, guardas por rol, recuperación y cambio de contraseña.
- Catálogo público responsivo, búsqueda, filtros, ficha de producto, cantidades y consulta por WhatsApp.
- CRUD administrativo de usuarios, expositores, categorías, productos e imágenes.
- Gestión de ferias, portada, galería, estados terminales y asignaciones de expositores.
- Portal del expositor para perfil, productos e imágenes propias.
- Componentes comunes, estados de carga/error/vacío, modal accesible, página 404 y límite global de errores.
- Carga diferida por ruta, pruebas unitarias, pruebas de componentes y recorridos E2E en escritorio/móvil.
- Matriz de cobertura disponible en `docs/MATRIZ_FRONTEND_API.md`.

Nota de contrato: aunque el plan del backend describe la portada como opcional, el esquema vigente `FairCreateSchema` exige `imagen_portada`. El formulario de creación la solicita para respetar el contrato ejecutable actual.

### Resultado de verificación

- `npm.cmd run lint`: aprobado.
- `npx.cmd tsc --noEmit`: aprobado.
- `npm.cmd test`: 13 pruebas aprobadas.
- `npm.cmd run test:e2e`: 32 pruebas aprobadas en Chromium, Edge, Firefox, WebKit y móvil; 8 capturas duplicadas omitidas intencionalmente.
- `npm.cmd run build`: aprobado con división de código por ruta.
- Backend SQLite: 25 pruebas aprobadas y 1 prueba PostgreSQL omitida porque el entorno no define `TEST_DATABASE_URL`.
- Capturas y manual: `docs/MANUAL_FRONTEND.md` y `docs/capturas/`.

## 1. Objetivo

Completar el frontend React/TypeScript para consumir íntegramente el backend Flask ya implementado y cubrir los requerimientos del documento de propuesta. La entrega debe ofrecer tres experiencias completas:

1. Catálogo público para visitantes.
2. Portal de gestión para administradores y superadministradores.
3. Portal propio para expositores.

El backend y `docs/API.md` serán la fuente de verdad del contrato. Cuando la propuesta original difiera del diseño ya consolidado, prevalecen estas reglas:

- Las ferias cambian automáticamente entre `DRAFT`, `PUBLISHED` y `FINISHED` según sus fechas.
- Una feria se puede cancelar definitivamente con `DISABLED`, pero no publicar manualmente.
- La participación se asigna por expositor mediante `FairExhibitor`.
- Todos los productos vigentes del expositor autorizado se muestran dinámicamente; no existe selección manual de productos por feria.
- WhatsApp recibe `items: [{ product_id, quantity }]` y solo permite productos disponibles de un mismo expositor.

## 2. Diagnóstico actual

### Ya disponible

- React 19, TypeScript, Vite, React Router, TanStack Query, React Hook Form, Zod, Axios, Tailwind y Vitest.
- Inicio de sesión, cambio obligatorio de contraseña y redirección según rol.
- Catálogo de feria activa, expositores y productos.
- Dashboard administrativo básico.
- Formularios iniciales de administradores, expositores, ferias, productos y categorías.
- Consulta inicial por WhatsApp.
- Tema institucional y diseño responsivo básico.

### Brechas críticas

- `AdminPortal.tsx` concentra demasiadas pantallas y lógica, lo que dificulta pruebas y mantenimiento.
- Hay textos con codificación dañada (`CatÃ¡logo`, `CategorÃ­as`, etc.).
- El frontend aún ofrece publicación manual de ferias, aunque el backend controla el estado por fechas.
- WhatsApp todavía envía `product_ids`; falta capturar y enviar cantidades.
- La portada de feria se pide como URL en vez de cargarse mediante `/uploads`.
- Faltan CRUD completos: consultar, editar, activar/desactivar, restablecer contraseña y eliminar según permisos.
- Faltan perfil del expositor, galería de productos, portada, orden y texto alternativo.
- Los listados no aprovechan paginación, búsqueda y filtros del backend.
- La sesión se elimina con `localStorage.clear()` sin invocar `/auth/logout`.
- Faltan guardas de rutas robustas, manejo global de 401/403, estados vacíos consistentes y recuperación de contraseña.
- Solo existen pruebas unitarias mínimas; no hay cobertura de componentes ni flujos integrados.

## 3. Arquitectura propuesta

Reorganizar gradualmente `frontend/src` sin detener el funcionamiento:

```text
src/
  app/              router, providers y configuración
  api/              cliente Axios, tipos, errores y servicios por recurso
  auth/             sesión, guardas, login y recuperación
  components/       botones, campos, modales, tablas y estados comunes
  layouts/          PublicLayout, AdminLayout y ExhibitorLayout
  features/
    catalog/
    dashboard/
    users/
    exhibitors/
    fairs/
    products/
    categories/
    audit/
  hooks/
  styles/
  test/
```

Reglas técnicas:

- Tipos TypeScript para cada respuesta y formulario; evitar `any`.
- Un servicio API por dominio y claves de TanStack Query centralizadas.
- Formularios con React Hook Form + Zod y errores de campo provenientes de `error/details`.
- Componentes reutilizables para tabla, paginación, búsqueda, confirmación, carga, vacío y error.
- Invalidar únicamente las consultas afectadas después de cada mutación.
- URLs de API y archivos resueltas desde variables de entorno.
- Accesibilidad: etiquetas asociadas, navegación por teclado, foco visible, textos alternativos y modales con foco controlado.

## 4. Fases de ejecución

### Fase 0 — Línea base y contrato

Objetivo: asegurar que el frontend existente compila y registrar el contrato real antes de ampliar funciones.

Tareas:

- Ejecutar `npm test`, `npm run lint` y `npm run build` y corregir la línea base.
- Crear una matriz endpoint → pantalla → rol → estado de implementación.
- Corregir la codificación UTF-8 de todos los textos.
- Tipar las respuestas paginadas y los errores del backend.
- Documentar variables `VITE_API_URL` y URL base de archivos en `.env.example`.

Criterio de aceptación: build, lint y pruebas pasan; no hay textos corruptos ni contratos ambiguos.

### Fase 1 — Base transversal, sesión y navegación

Objetivo: crear una base segura y reusable para las demás pantallas.

Tareas:

- Dividir el router y agregar `PublicRoute`, `AuthenticatedRoute` y `RoleRoute`.
- Restaurar la sesión con `/auth/me` al iniciar la aplicación.
- Interceptor Axios para agregar JWT, normalizar errores y redirigir ante 401.
- Cerrar sesión mediante `/auth/logout` y luego limpiar solo las claves de autenticación.
- Implementar “Olvidé mi contraseña” y “Restablecer contraseña”.
- Mantener el cambio obligatorio de contraseña y validar la contraseña con las mismas reglas del backend.
- Crear layouts distintos para administrador y expositor; ocultar opciones no autorizadas.
- Crear notificaciones, modal de confirmación y estados `loading/error/empty` comunes.

Criterio de aceptación: ningún usuario puede abrir por URL una pantalla ajena a su rol; login, restauración, cambio, recuperación y cierre de sesión funcionan de extremo a extremo.

### Fase 2 — Catálogo público y WhatsApp

Objetivo: completar la experiencia ciudadana descrita en RF-29 a RF-38 y RF-50 a RF-57.

Tareas:

- Mejorar la portada de feria activa con imagen opcional, fechas, lugar y galería.
- Mostrar un estado informativo cuando no exista feria activa.
- Agregar búsqueda de expositores por nombre y filtros disponibles en el backend.
- Mostrar categorías y permitir búsqueda/filtro de productos.
- Crear ficha o modal de producto con galería, categoría, precio, descripción y disponibilidad.
- Mostrar correctamente `AVAILABLE` y `OUT_OF_STOCK`; solo el primero puede seleccionarse.
- Sustituir la selección simple por una lista con cantidad positiva por producto.
- Enviar `items: [{ product_id, quantity }]` a `/public/whatsapp-query`.
- Conservar la selección al navegar dentro del mismo expositor y limpiarla al cambiar de expositor/feria.
- Añadir skeletons, imágenes de respaldo, diseño móvil y mensajes claros.
- Incorporar metadatos básicos: título de página, descripción y vista compartible por feria/expositor.

Criterio de aceptación: un visitante encuentra un expositor/producto, selecciona cantidades y abre WhatsApp con el mensaje generado por el backend; nunca consulta productos no disponibles o de expositores distintos.

### Fase 3 — Gestión administrativa completa

Objetivo: cubrir las operaciones administrativas del documento usando los endpoints actuales.

#### Usuarios administradores

- Listar con paginación, búsqueda y filtros.
- Crear respetando qué roles puede crear cada administrador.
- Consultar y editar datos.
- Activar/desactivar, restablecer contraseña y eliminar lógicamente con confirmación.
- Proteger las restricciones del último `SUPERADMIN` y mostrar el error del backend.

#### Expositores/empresas

- Listar, buscar, filtrar y paginar.
- Crear expositor y mostrar el resultado del envío de credenciales.
- Ver detalle, editar información, activar/desactivar y eliminar lógicamente.
- Mostrar estado de cuenta y estado del expositor de forma comprensible.

#### Categorías

- Crear, editar, activar/desactivar y eliminar.
- Impedir desde la interfaz el borrado cuando el backend indique que tiene productos.
- Usar categorías activas en formularios y permitir al administrador ver todas.

#### Productos supervisados

- Listar todos los productos con expositor, categoría, estado, búsqueda, filtros y paginación.
- Crear y editar productos en nombre de un expositor.
- Cambiar disponibilidad y eliminar lógicamente.
- Administrar imágenes según la Fase 5.

#### Auditoría y dashboard

- Agregar paginación y filtros de auditoría.
- Mejorar indicadores, actividad reciente y enlaces directos a pendientes.
- Refrescar datos después de cambios relevantes.

Criterio de aceptación: cada endpoint administrativo documentado tiene una acción visible o una decisión explícita de no exponerlo; los permisos y errores se presentan sin perder los datos del formulario.

### Fase 4 — Gestión de ferias

Objetivo: alinear completamente la interfaz con el ciclo automático implementado en backend.

Tareas:

- Crear feria con portada opcional cargada mediante `POST /uploads`, no mediante URL escrita a mano.
- Validar fechas y advertir rangos superpuestos con el mensaje devuelto por backend.
- Editar ferias `DRAFT` y `PUBLISHED`; bloquear controles en `FINISHED` y `DISABLED`.
- Eliminar el botón “Publicar como activa”. Mostrar estado calculado y explicación del ciclo por fechas.
- Permitir finalizar o cancelar solo mediante las transiciones admitidas y con confirmación explícita.
- Administrar galería con `/fairs/:id/images` y `/fair-images/:id`.
- Asignar expositores, listar participaciones y cambiar `AUTHORIZED`, `REVOKED` u otros estados admitidos.
- Editar stand, sector y observaciones.
- Explicar que los productos se derivan automáticamente del expositor autorizado y no se eligen por feria.
- Deshabilitar cambios de participantes en ferias terminales.

Criterio de aceptación: la interfaz nunca intenta activar manualmente una feria, no ofrece transiciones inválidas y refleja inmediatamente el catálogo resultante de fechas y autorizaciones.

### Fase 5 — Portal del expositor e imágenes

Objetivo: dar autonomía al emprendedor sin permitir acceso a datos de otra empresa.

Tareas:

- Crear dashboard propio con resumen de productos y estado de participación.
- Implementar edición del perfil mediante `GET/PATCH /exhibitor/profile`.
- Completar CRUD propio con `/exhibitor/products` y `/exhibitor/products/:id`.
- Simplificar el formulario de producto y añadir vista previa antes de guardar.
- Subir múltiples imágenes, elegir portada, ordenar, editar texto alternativo y eliminar.
- Mostrar progreso y validaciones de tipo/tamaño durante la carga.
- Permitir cambiar rápidamente disponibilidad desde listado y detalle.
- Confirmar eliminaciones y explicar su efecto inmediato en el catálogo.

Criterio de aceptación: el expositor administra perfil, productos e imágenes propios desde móvil o escritorio, y los cambios autorizados aparecen inmediatamente en la feria activa.

### Fase 6 — Calidad, rendimiento y entrega

Objetivo: cerrar los requerimientos no funcionales y preparar producción.

Tareas:

- Pruebas unitarias para validadores, sesión, normalización de errores y cantidades.
- Pruebas de componentes para formularios, tablas, filtros, modales y estados.
- Pruebas integradas con API simulada para roles, CRUD, feria y WhatsApp.
- Pruebas E2E de los recorridos críticos con Playwright o Cypress.
- Auditoría responsive en móvil, tableta y escritorio.
- Auditoría de accesibilidad y navegación por teclado.
- Carga diferida por ruta, optimización de imágenes y medición de carga menor a cinco segundos.
- Verificación en Chrome, Edge, Firefox y Safari.
- Configurar manejo de errores inesperados y página 404.
- Actualizar README y manuales de operación con capturas y flujos finales.

Criterio de aceptación: build de producción sin errores, recorridos críticos automatizados, sin vulneraciones de rol evidentes y cumplimiento verificable de RNF-05 a RNF-20 y RNF-26 a RNF-28.

## 5. Orden recomendado de entregas

| Entrega | Alcance demostrable | Prioridad |
|---|---|---|
| E1 | Contrato, UTF-8, sesión, guardas, errores y layouts | Crítica |
| E2 | Catálogo público, búsqueda, filtros, cantidades y WhatsApp | Crítica |
| E3 | CRUD de usuarios, expositores, categorías y productos | Alta |
| E4 | Ferias, galerías y asignaciones alineadas al ciclo automático | Alta |
| E5 | Perfil, productos e imágenes del expositor | Alta |
| E6 | Pruebas E2E, accesibilidad, rendimiento y documentación | Media/alta |

Cada entrega debe incluir: funcionalidad, estados de carga/error/vacío, validación, pruebas relevantes y actualización de la matriz de endpoints.

## 6. Casos de aceptación finales

1. Un administrador inicia sesión y solo ve acciones permitidas por su rol.
2. Un superadministrador crea y administra cuentas sin poder eliminar o inhabilitar al último superadministrador activo.
3. El administrador crea un expositor y este recibe o visualiza sus credenciales según la configuración de correo.
4. El administrador crea una feria futura, carga imágenes y asigna expositores sin activarla manualmente.
5. Al llegar la fecha, la feria se muestra como activa y solo aparecen expositores autorizados.
6. Los productos disponibles y agotados se derivan automáticamente; los inactivos no aparecen.
7. Revocar un expositor retira inmediatamente todos sus productos del catálogo.
8. El expositor edita su perfil y solo sus propios productos e imágenes.
9. Un visitante busca productos, indica cantidades y abre una consulta válida por WhatsApp.
10. Al finalizar o cancelar la feria, el catálogo deja de mostrarla y la interfaz bloquea operaciones incompatibles.
11. Todos los listados grandes funcionan con paginación, filtros y estados vacíos.
12. Los flujos críticos funcionan en móvil y escritorio, con teclado y mensajes claros.

## 7. Definición de terminado

Una tarea se considera terminada cuando:

- Consume el endpoint y formato vigentes de `docs/API.md`.
- Respeta rol, propiedad y estados terminales.
- Incluye carga, éxito, vacío, validación y error.
- No introduce `any` sin justificación ni texto con codificación incorrecta.
- Tiene pruebas proporcionales al riesgo.
- Pasa `npm test`, `npm run lint` y `npm run build`.
- Se verifica al menos en vista móvil y escritorio.
- La documentación afectada queda actualizada.
