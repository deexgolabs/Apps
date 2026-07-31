"""Fila de background pra tarefas que não devem bloquear a resposta HTTP nem
travar a rota principal se falharem (e-mail, push, futuro webhook de saída
do dono -- #188). Persistida no Postgres (já disponível, sem exigir
Redis/RabbitMQ/Celery) e processada por um worker assíncrono simples rodando
dentro do próprio processo do backend -- correto pra esta implantação, já que
o Render roda um único processo (WEB_CONCURRENCY=1). Falhas transitórias são
reenfileiradas com backoff exponencial até max_attempts; depois disso o job
fica marcado como "failed" pra investigação manual, sem tentar pra sempre."""
import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import BackgroundJob, utcnow

logger = logging.getLogger("app.jobs")

BATCH_SIZE = 20
BACKOFF_BASE_MINUTES = 2  # tentativas em 2, 4, 8, 16, 32... minutos


def enqueue_job(db: Session, job_type: str, payload: dict, max_attempts: int = 5) -> BackgroundJob:
    job = BackgroundJob(job_type=job_type, payload=payload, max_attempts=max_attempts, next_attempt_at=utcnow())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _execute(job: BackgroundJob, db: Session) -> None:
    """Despacha o job de verdade por tipo -- levanta exceção em caso de falha,
    quem chama (run_pending_jobs) decide o que fazer com isso."""
    if job.job_type == "email":
        from app.email_utils import send_email_now
        send_email_now(to=job.payload["to"], subject=job.payload["subject"], html_body=job.payload["html_body"])
    elif job.job_type == "push":
        from app.routes.push import send_push_now
        send_push_now(job.payload["app_id"], job.payload["end_user_id"], job.payload["title"], job.payload["body"], db)
    elif job.job_type == "webhook":
        import httpx
        response = httpx.post(job.payload["url"], json=job.payload["body"], timeout=10.0)
        response.raise_for_status()
    else:
        raise ValueError(f"Tipo de job desconhecido: {job.job_type}")


def run_pending_jobs(db: Session) -> int:
    """Roda um lote de jobs pendentes cujo next_attempt_at já chegou. Retorna
    quantos foram processados (sucesso ou falha -- não conta os que ainda não
    estão prontos pra tentar). Chamado pelo worker em loop (main.py) ou
    diretamente nos testes."""
    jobs = (
        db.query(BackgroundJob)
        .filter(BackgroundJob.status == "pending", BackgroundJob.next_attempt_at <= utcnow())
        .order_by(BackgroundJob.created_at)
        .limit(BATCH_SIZE)
        .all()
    )
    for job in jobs:
        job.attempts += 1
        try:
            _execute(job, db)
            job.status = "done"
            job.last_error = None
        except Exception as exc:
            job.last_error = str(exc)[:500]
            if job.attempts >= job.max_attempts:
                job.status = "failed"
                logger.error(
                    "Job %s (%s) falhou definitivamente após %s tentativa(s): %s",
                    job.id, job.job_type, job.attempts, exc,
                )
            else:
                backoff_minutes = BACKOFF_BASE_MINUTES * (2 ** (job.attempts - 1))
                job.next_attempt_at = utcnow() + timedelta(minutes=backoff_minutes)
                logger.warning(
                    "Job %s (%s) falhou (tentativa %s/%s), nova tentativa em %s min: %s",
                    job.id, job.job_type, job.attempts, job.max_attempts, backoff_minutes, exc,
                )
        db.commit()
    return len(jobs)
