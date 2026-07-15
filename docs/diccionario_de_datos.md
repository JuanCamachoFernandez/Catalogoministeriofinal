# Diccionario de datos

Los campos `created_at` y `updated_at` de los modelos principales son `TIMESTAMP WITH TIME ZONE`, obligatorios y generados automáticamente; `deleted_at` es opcional.

| Tabla | PK | FK principales | Campos únicos | Propósito |
|---|---|---|---|---|
| users | id UUID | — | username, email | Identidad y autenticación |
| admin_profiles | id UUID | user_id | user_id | Perfil laboral administrativo |
| exhibitors | id UUID | user_id | user_id, numero_documento, email_gmail | Identidad comercial y WhatsApp |
| exhibitor_types | id UUID | — | nombre | Clasificaciones |
| exhibitor_type_links | id UUID | exhibitor_id, type_id | par exhibitor/type | Relación N:M |
| fairs | id UUID | created_by | slug | Ferias |
| fair_images | id UUID | fair_id | — | Galería de feria |
| fair_exhibitors | id UUID | fair_id, exhibitor_id, authorized_by | par fair/exhibitor | Asignación y autorización |
| categories | id UUID | — | nombre, slug | Categorías |
| products | id UUID | exhibitor_id, category_id | par exhibitor/slug | Productos sin precio ni cantidad |
| product_images | id UUID | product_id | — | Galería de producto |
| password_recoveries | id UUID | user_id | token_hash | Tokens hasheados |
| audits | id UUID | user_id | — | Trazabilidad |

La definición campo por campo autoritativa está en `backend/app/models.py`; los tipos, nulabilidad y valores predeterminados se generan desde esa metadata mediante Alembic.
