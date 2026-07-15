# Base de datos

El sistema usa PostgreSQL 16, sugerido como `catalogo_ferias`, conectado con `postgresql+psycopg`. SQLAlchemy 2 define UUID, claves foráneas, restricciones e índices; Flask-Migrate/Alembic administra versiones. Las marcas de tiempo son UTC con zona y la interfaz presenta `America/La_Paz`.

Contraseñas: Argon2. Tokens: solo hash. Registros de negocio emplean estado y `deleted_at`. Las restricciones únicas protegen usuarios, correos, documentos, slugs y asignaciones duplicadas. Respaldar con `pg_dump` y restaurar con `pg_restore`; las imágenes se respaldan aparte.

Las tablas reales son: users, admin_profiles, exhibitors, exhibitor_types, exhibitor_type_links, fairs, fair_images, fair_exhibitors, categories, products, product_images, password_recoveries y audits.
