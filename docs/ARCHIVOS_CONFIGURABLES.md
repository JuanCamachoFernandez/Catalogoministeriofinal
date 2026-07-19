# Archivos configurables

| Archivo | Uso | Qué editar |
|---|---|---|
| `backend/.env` | Backend privado | PostgreSQL, secretos JWT, Brevo API, URL y carga |
| `frontend/.env` | Frontend | `VITE_DIRECCION_SERVICIO`, nombre y código 591 |
| `frontend/tailwind.config.js` | Identidad visual | colores y tipografía |

Variables backend: `CLAVE_SECRETA_APLICACION`, `CLAVE_SECRETA_SESIONES`, `DIRECCION_BASE_DATOS`, `DIRECCION_INTERFAZ_WEB`, `ORIGENES_PERMITIDOS`, `CARPETA_CARGAS`, `TAMANO_MAXIMO_CONTENIDO`, `USUARIO_ADMINISTRADOR_INICIAL`, `NOMBRES_ADMINISTRADOR_INICIAL`, `APELLIDO_PATERNO_ADMINISTRADOR_INICIAL`, `APELLIDO_MATERNO_ADMINISTRADOR_INICIAL`, `CORREO_ADMINISTRADOR_INICIAL`, `CONTRASENA_ADMINISTRADOR_INICIAL`, `CLAVE_BREVO`, `CORREO_REMITENTE_BREVO`, `NOMBRE_REMITENTE_BREVO` y `ENVIO_CORREO_HABILITADO`.

`backend/.env` contiene datos privados. `backend/.env.example` documenta los nombres sin valores reales. En frontend, `VITE_DIRECCION_SERVICIO` apunta a `http://localhost:5000/api`, `VITE_NOMBRE_APLICACION` cambia el nombre visible y `VITE_CODIGO_PAIS_PREDETERMINADO=591` conserva Bolivia.
