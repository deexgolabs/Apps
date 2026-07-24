import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("app.email")


def send_email(to: str, subject: str, html_body: str) -> None:
    """Envia um e-mail via SMTP. Se SMTP não estiver configurado (.env vazio),
    apenas loga o conteúdo — útil em dev sem servidor de e-mail real."""
    if not settings.smtp_host:
        # print() em vez de logger.info(): sem handler configurado no root logger,
        # .info() é descartado silenciosamente (nível padrão é WARNING) — isso é
        # justamente o fallback visível para dev sem SMTP real, então precisa aparecer.
        print(f"\n--- E-MAIL (SMTP não configurado, apenas exibindo) ---\nPara: {to}\nAssunto: {subject}\n{html_body}\n---\n")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to
    message.set_content(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
