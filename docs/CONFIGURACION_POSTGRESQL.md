# Configuración de PostgreSQL

Instale PostgreSQL 16 o superior y conserve la contraseña administrativa. Desde pgAdmin o `psql` ejecute:

```sql
CREATE USER catalogo WITH PASSWORD 'CONTRASENA_LOCAL_SEGURA';
CREATE DATABASE catalogo_ferias OWNER catalogo;
GRANT ALL PRIVILEGES ON DATABASE catalogo_ferias TO catalogo;
```

En `backend/.env` configure:

```env
DATABASE_URL=postgresql+psycopg://catalogo:CONTRASENA_LOCAL_SEGURA@localhost:5432/catalogo_ferias
```

Si la contraseña contiene caracteres reservados de URL, codifíquelos. Compruebe la conexión con `flask db current`; aplique cambios con `flask db upgrade`. Nunca elimine la base ni las migraciones para resolver un error sin realizar antes un respaldo.
