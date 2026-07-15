"""Envío transaccional mediante la API HTTP de Brevo; no usa SMTP."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmailDeliveryError(RuntimeError):
    pass


class BrevoEmailService:
    endpoint = "https://api.brevo.com/v3/smtp/email"

    def __init__(self):
        self.api_key = os.getenv("BREVO_API_KEY", "").strip()
        self.sender_email = os.getenv("BREVO_SENDER_EMAIL", "").strip()
        self.sender_name = os.getenv(
            "BREVO_SENDER_NAME", "Catálogo Digital de Ferias"
        ).strip()
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

    def send(self, recipient_email, recipient_name, subject, html_content):
        if not self.enabled:
            return {"sent": False, "reason": "EMAIL_ENABLED=false"}
        if not self.api_key or not self.sender_email:
            raise EmailDeliveryError(
                "Configure BREVO_API_KEY y BREVO_SENDER_EMAIL en backend/.env"
            )
        payload = json.dumps(
            {
                "sender": {"name": self.sender_name, "email": self.sender_email},
                "to": [{"email": recipient_email, "name": recipient_name}],
                "subject": subject,
                "htmlContent": html_content,
            }
        ).encode("utf-8")
        request = Request(
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
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                return {"sent": True, "message_id": result.get("messageId")}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise EmailDeliveryError(f"Brevo rechazó el envío ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise EmailDeliveryError("No se pudo conectar con la API de Brevo") from exc

    def send_credentials(self, email, name, username, temporary_password):
        return self.send(
            email,
            name,
            "Credenciales de acceso",
            f"<p>Hola {name},</p><p>Usuario: <strong>{username}</strong></p>"
            f"<p>Contraseña temporal: <strong>{temporary_password}</strong></p>"
            "<p>El sistema le solicitará cambiarla en su primer ingreso.</p>",
        )

    def send_password_changed(self, email, name):
        return self.send(
            email,
            name,
            "Contraseña actualizada",
            f"<p>Hola {name},</p><p>Su contraseña fue actualizada correctamente.</p>",
        )
