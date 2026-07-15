# Seguridad

- Contraseñas almacenadas con Argon2.
- Identificadores UUID.
- JWT para autenticación y control de rol en backend.
- Cambio obligatorio de contraseña temporal.
- SQLAlchemy parametriza consultas y reduce riesgo de inyección SQL.
- CORS restringido mediante `CORS_ORIGINS`.
- WhatsApp deriva el teléfono desde la propiedad del producto; el cliente no envía el destinatario.
- Brevo usa HTTPS y la clave permanece en `backend/.env`.
- No se devuelven `password_hash`, claves JWT ni credenciales Brevo.

No publique `backend/.env`, respaldos, tokens ni datos personales. Para compartir una instalación completa, envíe el `.env` por un canal privado y use el repositorio para código y plantillas `.env.example`.
