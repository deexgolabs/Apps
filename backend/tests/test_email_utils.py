import threading
import time

from app import email_utils


def test_send_email_without_smtp_configured_prints_and_returns_immediately(monkeypatch, capsys):
    monkeypatch.setattr(email_utils.settings, "smtp_host", "")
    threads_before = threading.active_count()

    email_utils.send_email(to="cliente@example.com", subject="Assunto", html_body="<p>Oi</p>")

    captured = capsys.readouterr()
    assert "cliente@example.com" in captured.out
    assert threading.active_count() == threads_before


def test_send_email_with_smtp_configured_never_blocks_the_caller(monkeypatch):
    """Regressão: smtplib.SMTP() sem timeout podia travar por minutos, e como
    send_email() era chamado direto (sem await) de dentro de rotas async, isso
    travava o event loop inteiro do servidor. Esse teste garante que
    send_email() sempre retorna na hora, mesmo que o envio de verdade demore
    (ou trave) -- o trabalho pesado tem que rodar em background."""
    monkeypatch.setattr(email_utils.settings, "smtp_host", "smtp.exemplo.com")
    monkeypatch.setattr(email_utils.settings, "smtp_user", "")

    release_event = threading.Event()
    call_args = {}

    class _BlockingSMTP:
        def __init__(self, host, port, timeout=None):
            call_args["host"] = host
            call_args["port"] = port
            call_args["timeout"] = timeout

        def __enter__(self):
            release_event.wait(timeout=5)  # simula uma conexão SMTP lenta/travada
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            pass

        def send_message(self, message):
            call_args["sent"] = True

    monkeypatch.setattr(email_utils.smtplib, "SMTP", _BlockingSMTP)

    start = time.monotonic()
    email_utils.send_email(to="cliente@example.com", subject="Assunto", html_body="<p>Oi</p>")
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, "send_email() bloqueou o chamador em vez de rodar em background"

    release_event.set()
    for _ in range(50):
        if call_args.get("sent"):
            break
        time.sleep(0.05)
    assert call_args.get("sent") is True
    assert call_args["timeout"] == email_utils.SMTP_TIMEOUT_SECONDS


def test_send_email_logs_but_does_not_raise_on_smtp_failure(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "smtp_host", "smtp.exemplo.com")

    class _FailingSMTP:
        def __init__(self, host, port, timeout=None):
            raise ConnectionRefusedError("boom")

    monkeypatch.setattr(email_utils.smtplib, "SMTP", _FailingSMTP)

    # não deve levantar exceção pro chamador -- o erro é só logado
    email_utils.send_email(to="cliente@example.com", subject="Assunto", html_body="<p>Oi</p>")
    time.sleep(0.2)
