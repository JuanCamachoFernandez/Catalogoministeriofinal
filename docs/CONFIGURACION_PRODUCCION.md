# Configuración de producción local o en servidor

Use PostgreSQL independiente, secretos aleatorios largos, CORS limitado al dominio real y HTTPS delante de Flask. No utilice los valores de ejemplo. Ejecute `npm run build` y sirva `frontend/dist` mediante un servidor web; ejecute Flask con un servidor WSGI compatible con Windows o Linux.

Mantenga `backend/uploads` en almacenamiento persistente, programe respaldos de PostgreSQL, rote secretos ante una exposición y limite acceso al archivo `.env`. Verifique Brevo, migraciones y `/api/health` antes de habilitar tráfico.

Programe `flask sync-fairs` al menos una vez al día, idealmente cada 15 minutos. El comando sincroniza estados, elimina imágenes huérfanas y purga tokens revocados expirados. Debe ejecutarse desde `backend` con el mismo entorno virtual y `.env` del servicio.

La caché pública usa una versión compartida en PostgreSQL, por lo que varios procesos WSGI observan invalidaciones sin Redis. `SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA` permite cambiar el valor predeterminado de 60 segundos.
