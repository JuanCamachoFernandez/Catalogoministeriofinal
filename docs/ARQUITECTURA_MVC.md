# Arquitectura MVC del backend

El backend Flask utiliza MVC adaptado a una API REST.

## Modelo

`backend/app/models/` contiene las entidades SQLAlchemy, enums, relaciones y reglas de dominio. `Fair` define estados terminales, estado esperado por fechas y detección de solapamientos. `models/__init__.py` conserva una interfaz estable para migraciones y pruebas.

## Vista

`backend/app/views/` transforma modelos en respuestas JSON y centraliza el formato de errores. Esta capa no contiene rutas HTTP ni decisiones de autorización.

## Controlador

`backend/app/controllers/` contiene blueprints separados para autenticación, administración, ferias, expositores, productos, categorías, archivos y catálogo público. Los controladores validan permisos, coordinan operaciones y delegan la presentación a las vistas.

La fábrica `create_app` registra todos los controladores y configura SQLAlchemy, Alembic, JWT, CORS y la lista persistente de tokens revocados.

## Reglas principales

- No existe `FairProduct`: los productos se derivan de la participación autorizada del expositor.
- Una feria se publica automáticamente dentro de su rango de fechas.
- Las ferias finalizadas o canceladas son inmutables y no conservan imágenes físicas.
- Los archivos se validan como imágenes reales y se restringen al directorio configurado.
- Las mutaciones relevantes invalidan el caché público y generan auditoría.
