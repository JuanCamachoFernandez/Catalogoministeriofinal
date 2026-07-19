"""Envío transaccional mediante la API HTTP de Brevo; no usa SMTP."""

import json
import os
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmailDeliveryError(RuntimeError):
    pass


class BrevoEmailService:
    endpoint = "https://api.brevo.com/v3/smtp/email"

    def __init__(self):
        self.api_key = os.getenv("CLAVE_BREVO", "").strip()
        self.sender_email = os.getenv("CORREO_REMITENTE_BREVO", "").strip()
        self.sender_name = os.getenv(
            "NOMBRE_REMITENTE_BREVO", "Catálogo Digital de Ferias"
        ).strip()
        self.enabled = os.getenv("ENVIO_CORREO_HABILITADO", "false").lower() == "true"

    def send(self, recipient_email, recipient_name, subject, html_content):
        if not self.enabled:
            return {"sent": False, "reason": "ENVIO_CORREO_HABILITADO=false"}
        if not self.api_key or not self.sender_email:
            raise EmailDeliveryError(
                "Configure CLAVE_BREVO y CORREO_REMITENTE_BREVO en backend/.env"
            )
        payload = json.dumps(
            {
                "sender": {"name": self.sender_name, "email": self.sender_email},
                "to": [{"email": recipient_email, "name": recipient_name}],
                "subject": subject,
                "htmlContent": html_content,
            }
        ).encode("utf-8")
        brevo_request = Request(
            self.endpoint,
            data=payload,
            method="POST",
            headers={
                "accept": "application/json",
                "api-key": self.api_key,
                "content-type": "application/json",
            },
        )
        try:
            with urlopen(brevo_request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                return {"sent": True, "message_id": result.get("messageId")}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise EmailDeliveryError(
                f"Brevo rechazó el envío ({exc.code}): {detail}"
            ) from exc
        except URLError as exc:
            raise EmailDeliveryError("No se pudo conectar con la API de Brevo") from exc

    def send_password_code(self, email, name, code):
        safe_name = escape(name)
        return self.send(
            email,
            safe_name,
            "Código para recuperar su contraseña",
            f"<div style=\"font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1f2933\">"
            f"<h2 style=\"color:#17324d\">Recuperación de contraseña</h2>"
            f"<p>Hola {safe_name},</p>"
            "<p>Recibimos una solicitud para cambiar la contraseña de su cuenta en el "
            "Catálogo Digital de Ferias. Ingrese el siguiente código en la pantalla de recuperación:</p>"
            f"<p style=\"margin:28px 0;text-align:center;font-size:32px;font-weight:800;"
            f"letter-spacing:10px;color:#236132\">{code}</p>"
            "<p>El código vence en 10 minutos y solo puede utilizarse una vez. "
            "Si usted no realizó esta solicitud, ignore este mensaje y no comparta el código con nadie.</p>"
            "<p style=\"color:#697680;font-size:13px\">Este es un mensaje automático; no responda a este correo.</p>"
            "</div>",
        )
