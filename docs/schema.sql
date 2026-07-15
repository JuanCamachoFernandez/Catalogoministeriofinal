-- Esquema de referencia PostgreSQL. La fuente autoritativa es la migración generada
-- desde backend/app/models.py con: flask db migrate -m "esquema inicial".
CREATE TYPE user_role AS ENUM ('SUPERADMIN','ADMIN_VICEMINISTERIO','EXPOSITOR');
CREATE TYPE user_status AS ENUM ('ACTIVE','INACTIVE','LOCKED');
CREATE TYPE fair_status AS ENUM ('DRAFT','PUBLISHED','DISABLED','FINISHED');
CREATE TYPE assignment_status AS ENUM ('PENDING','AUTHORIZED','REJECTED','REVOKED');
CREATE TYPE product_status AS ENUM ('AVAILABLE','OUT_OF_STOCK','INACTIVE','DELETED');
CREATE TYPE document_type AS ENUM ('CI','NIT','OTRO');
-- Para evitar divergencia, genere el DDL completo desde una base migrada:
-- pg_dump --schema-only -U catalogo -d catalogo_ferias > docs/schema.sql
