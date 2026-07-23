# Configuración de Brevo

El sistema consume Brevo Transactional Email API mediante HTTPS desde `backend/app/email_service.py`. No utiliza SMTP, Gmail API, Google Cloud ni OAuth de Google.

Variables privadas en `backend/.env`:

```env
CLAVE_BREVO=
CORREO_REMITENTE_BREVO=
NOMBRE_REMITENTE_BREVO=Ferias Productivas Bolivia
ENVIO_CORREO_HABILITADO=false
```

## Brevo ya configurado

Si estas variables ya contienen credenciales válidas, no las reemplace, copie ni publique. Verifique únicamente que el remitente esté validado en Brevo y use `ENVIO_CORREO_HABILITADO=true`. Para detener temporalmente envíos use `false`.

La clave se obtiene en **Settings → SMTP & API → API Keys**, pero el proyecto usa la pestaña API y nunca las credenciales SMTP. El remitente se verifica en **Senders & IP**. Las pruebas automatizadas no deben hacer envíos reales.

Si Brevo no responde, la aplicación debe mostrar un error controlado sin revelar la respuesta completa ni la API key. Para rotar una clave, cree una nueva en Brevo, actualice únicamente el `.env` privado, pruebe y revoque la anterior.
