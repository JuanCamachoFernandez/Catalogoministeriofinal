# Configuración de producción local o en servidor

Use PostgreSQL independiente, secretos aleatorios largos, `FLASK_ENV=production`, CORS limitado al dominio real y HTTPS delante de Flask. No utilice los valores de ejemplo. Ejecute `npm run build` y sirva `frontend/dist` mediante un servidor web; ejecute Flask con un servidor WSGI compatible con Windows o Linux.

Mantenga `backend/uploads` en almacenamiento persistente, programe respaldos de PostgreSQL, rote secretos ante una exposición y limite acceso al archivo `.env`. Verifique Brevo, migraciones y `/api/health` antes de habilitar tráfico.
