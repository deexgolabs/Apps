import logging
import smtplib
import threading
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("app.email")

# smtplib.SMTP() sem timeout pode travar a conexão TCP por vários MINUTOS
# quando o host SMTP não responde (comum em produção sem SMTP configurado
# de verdade) -- e como send_email() é chamado direto (sem await) de dentro
# de rotas async, isso travava a MESMA thread do event loop e derrubava o
# servidor inteiro (nenhuma outra requisição era atendida) até o timeout
# estourar. Por isso o envio de verdade roda numa thread separada: a chamada
# de send_email() sempre retorna na hora, e o pior caso vira "essa thread
# específica demora", não "o servidor inteiro trava".
SMTP_TIMEOUT_SECONDS = 10


def _send_smtp(to: str, subject: str, html_body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to
    message.set_content(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except Exception:
        logger.exception("Falha ao enviar e-mail para %s", to)


def send_email(to: str, subject: str, html_body: str) -> None:
    """Envia um e-mail via SMTP em background (thread separada, nunca bloqueia
    quem chamou). Se SMTP não estiver configurado (.env vazio), apenas loga o
    conteúdo na hora — útil em dev sem servidor de e-mail real."""
    if not settings.smtp_host:
        # print() em vez de logger.info(): sem handler configurado no root logger,
        # .info() é descartado silenciosamente (nível padrão é WARNING) — isso é
        # justamente o fallback visível para dev sem SMTP real, então precisa aparecer.
        print(f"\n--- E-MAIL (SMTP não configurado, apenas exibindo) ---\nPara: {to}\nAssunto: {subject}\n{html_body}\n---\n")
        return

    threading.Thread(target=_send_smtp, args=(to, subject, html_body), daemon=True).start()
