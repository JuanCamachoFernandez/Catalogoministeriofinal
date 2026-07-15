# Archivos configurables

| Archivo | Uso | Qué editar |
|---|---|---|
| `backend/.env` | Backend privado | PostgreSQL, secretos JWT, Brevo API, URL y carga |
| `frontend/.env` | Frontend | `VITE_API_URL`, nombre y código 591 |
| `frontend/tailwind.config.js` | Identidad visual | colores y tipografía |

Variables backend: `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, `UPLOAD_FOLDER`, `MAX_CONTENT_LENGTH`, las cuatro `INITIAL_ADMIN_*`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` y `EMAIL_ENABLED`.

`backend/.env` contiene datos privados. `backend/.env.example` documenta los nombres sin valores reales. En frontend, `VITE_API_URL` apunta a `http://localhost:5000/api`, `VITE_APP_NAME` cambia el nombre visible y `VITE_DEFAULT_COUNTRY_CODE=591` conserva Bolivia.
