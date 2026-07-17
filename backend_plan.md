# Plan backend MVC, ferias automáticas y validación Postman

  ## Resumen

  Se completará primero el backend y se congelará su contrato antes de retomar React. El primer trabajo será convertir la estructura actual en MVC estricto sin cambiar
  comportamiento; después se implementará el ciclo automático de ferias y la participación derivada de productos.

  No se creará FairProduct: todos los productos vigentes del expositor autorizado se obtendrán dinámicamente mediante FairExhibitor + Product.

  ## 1. Reorganización MVC

  La aplicación quedará organizada así:

  backend/app/
  ├── models/
  │   ├── user.py
  │   ├── exhibitor.py
  │   ├── fair.py
  │   ├── product.py
  │   ├── category.py
  │   ├── audit.py
  │   └── __init__.py
  ├── views/
  │   ├── auth_view.py
  │   ├── fair_view.py
  │   ├── exhibitor_view.py
  │   ├── product_view.py
  │   ├── category_view.py
  │   └── error_view.py
  ├── controllers/
  │   ├── auth_controller.py
  │   ├── admin_controller.py
  │   ├── fair_controller.py
  │   ├── exhibitor_controller.py
  │   ├── product_controller.py
  │   ├── category_controller.py
  │   └── public_controller.py
  ├── config.py
  ├── extensions.py
  ├── commands.py
  └── __init__.py

  - Models: entidades SQLAlchemy, relaciones, consultas de dominio y reglas de negocio.
  - Views: esquemas Marshmallow, validación de entrada y serialización uniforme de JSON.
  - Controllers: rutas Flask, autenticación, autorización y coordinación entre petición, modelo y vista.
  - Mantener configuración, extensiones, comandos, correo y almacenamiento como soporte técnico.
  - Eliminar gradualmente el api.py monolítico después de registrar todos los nuevos blueprints.
  - Conservar las importaciones públicas desde app.models mediante models/__init__.py, evitando romper pruebas y migraciones.
  - Mantener inicialmente las rutas HTTP existentes para no afectar al frontend.
  - Ejecutar todas las pruebas después del refactor antes de añadir comportamiento nuevo.

  ## 2. Ferias, imágenes y catálogo

  - Sincronizar estados con la fecha local America/La_Paz:
      - DRAFT antes de fecha_inicio.
      - PUBLISHED entre inicio y fin, inclusive.
      - FINISHED después de fecha_fin.
      - DISABLED para cancelación definitiva.

  - Rechazar rangos superpuestos entre ferias no terminales.
  - Permitir edición en DRAFT y PUBLISHED; bloquear FINISHED y DISABLED.
  - Una feria publicada no podrá regresar a preparación ni mover su inicio al futuro.
  - No permitir reactivación de ferias finalizadas o canceladas.
  - Ejecutar sincronización al consultar catálogo, ferias o dashboard.
  - Añadir flask sync-fairs para ejecución periódica en producción.
  - Hacer nullable fairs.imagen_portada.
  - Al finalizar o cancelar:
      - Mantener el registro histórico de la feria y sus asignaciones.
      - Eliminar físicamente portada y galería.
      - Establecer imagen_portada = NULL.
      - Eliminar registros FairImage.
      - No modificar usuarios, expositores ni productos.

  - Aceptar únicamente archivos locales administrados por /api/uploads para imágenes de feria.
  - Impedir borrados fuera de UPLOAD_FOLDER/ferias.
  - Limpiar archivos huérfanos mediante sync-fairs.
  - Auditar activaciones, finalizaciones, cancelaciones y limpieza de archivos.

  ## 3. Productos y operaciones pendientes

  - Mantener FairExhibitor como única asignación de participación.
  - Publicar productos AVAILABLE y OUT_OF_STOCK del expositor AUTHORIZED.
  - Excluir productos inactivos, eliminados o pertenecientes a expositores no autorizados.
  - Reflejar inmediatamente altas, ediciones, precios, imágenes, disponibilidad y eliminación.
  - Retirar todos los productos al revocar o rechazar al expositor.
  - Bloquear modificaciones de participantes en ferias terminales.
  - Completar consulta individual, edición y eliminación lógica de usuarios, expositores, productos y categorías.
  - Añadir GET/PATCH /api/exhibitor/profile.
  - Completar imágenes de producto: listado, portada única, orden, texto alternativo y eliminación física.
  - Permitir eliminar categorías solamente cuando no tengan productos.
  - Completar recuperación y restablecimiento de contraseña.
  - Implementar revocación de JWT y control de intentos fallidos.
  - Integrar Brevo para credenciales y recuperación.
  - Cambiar WhatsApp a items: [{product_id, quantity}], validando cantidades positivas, feria activa y un solo expositor.
  - Incorporar paginación, búsqueda y filtros públicos.
  - Añadir caché backend con invalidación al cambiar ferias, asignaciones, expositores, productos o imágenes.

  ## 4. Pruebas automáticas y Postman

  - Mantener pruebas rápidas con SQLite para reglas aisladas.
  - Añadir pruebas de integración con una base PostgreSQL separada.
  - Ejecutar migraciones desde cero sobre PostgreSQL de pruebas antes de validar endpoints.
  - Usar un directorio temporal para probar cargas y eliminaciones físicas.
  - Añadir comandos de semilla y reinicio que solo funcionen cuando la base termine en _test.
  - Cubrir con pytest:
      - Roles, propiedad de datos y JWT.
      - Recuperación de contraseña.
      - Límites de fechas y transiciones automáticas.
      - Solapamiento de ferias.
      - Irreversibilidad de estados terminales.
      - Eliminación segura de imágenes.
      - Productos derivados y revocación de expositores.
      - WhatsApp con cantidades.
      - Caché e invalidación.
      - CRUD y errores de validación.

  postman/
  ├── CatalogoMinisterio.postman_collection.json
  ├── CatalogoMinisterio.test.postman_environment.json
  └── README.md

  La colección incluirá todos los endpoints organizados por módulo. Los flujos importantes quedarán automatizados y visibles:

  1. Estado de API e inicio de sesión.
  2. Creación de categoría, expositor y producto.
  3. Subida de portada y creación de feria.
  4. Asignación del expositor.
  5. Consulta pública de feria, expositor y producto.
  6. Edición y disponibilidad reflejadas públicamente.
  7. Consulta WhatsApp con cantidad.
  8. Revocación y reautorización del expositor.
  9. Finalización de feria y desaparición del catálogo.
  10. Verificación de que las imágenes fueron retiradas.
  11. Casos negativos de permisos, propiedad y validación.

  - La colección capturará tokens, IDs y slugs automáticamente en variables.
  - El entorno no contendrá secretos ni credenciales reales.
  - Postman se ejecutará únicamente contra PostgreSQL de pruebas.
  - Se documentarán los pasos para reiniciar la base, iniciar Flask, importar la colección y ejecutar el flujo.
  - Las mismas pruebas críticas podrán ejecutarse por consola con Newman o Postman CLI cuando esté disponible.

  ## Supuestos fijados

  - MVC será explícito y estricto; no se añadirá una carpeta services.
  - Las reglas de negocio estarán en modelos y los controladores no harán consultas SQL directas complejas.
  - Las vistas del backend son serializadores JSON, no componentes React.
  - No habrá FairProduct ni selección manual de productos.
  - Las ferias históricas se conservan, pero sin archivos de imagen.
  - Inicio y fin son fechas inclusivas en horario boliviano.
  - Las ferias terminales son inmutables.
  - Los cambios locales actuales del frontend quedan fuera de esta etapa.