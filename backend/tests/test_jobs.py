from datetime import timedelta

from app.jobs import enqueue_job, run_pending_jobs
from app.models import BackgroundJob, utcnow


def test_enqueue_job_creates_pending_row(db_session):
    job = enqueue_job(db_session, "email", {"to": "a@example.com", "subject": "s", "html_body": "b"})
    assert job.status == "pending"
    assert job.attempts == 0
    assert job.max_attempts == 5

    row = db_session.query(BackgroundJob).filter(BackgroundJob.id == job.id).first()
    assert row.payload == {"to": "a@example.com", "subject": "s", "html_body": "b"}


def test_run_pending_jobs_marks_done_on_success(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.email_utils.send_email_now",
        lambda to, subject, html_body: calls.append((to, subject, html_body)),
    )

    job = enqueue_job(db_session, "email", {"to": "a@example.com", "subject": "oi", "html_body": "<p>x</p>"})
    processed = run_pending_jobs(db_session)

    assert processed == 1
    assert calls == [("a@example.com", "oi", "<p>x</p>")]
    db_session.refresh(job)
    assert job.status == "done"
    assert job.attempts == 1
    assert job.last_error is None


def test_run_pending_jobs_retries_with_backoff_on_failure(db_session, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("SMTP fora do ar")

    monkeypatch.setattr("app.email_utils.send_email_now", _boom)

    job = enqueue_job(db_session, "email", {"to": "a@example.com", "subject": "s", "html_body": "b"}, max_attempts=5)
    before = utcnow()
    run_pending_jobs(db_session)

    db_session.refresh(job)
    assert job.status == "pending"
    assert job.attempts == 1
    assert job.last_error == "SMTP fora do ar"
    assert job.next_attempt_at > before + timedelta(minutes=1)


def test_run_pending_jobs_marks_failed_after_max_attempts(db_session, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("falha permanente")

    monkeypatch.setattr("app.email_utils.send_email_now", _boom)

    job = enqueue_job(db_session, "email", {"to": "a@example.com", "subject": "s", "html_body": "b"}, max_attempts=1)
    run_pending_jobs(db_session)

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.attempts == 1


def test_run_pending_jobs_skips_jobs_not_yet_due(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr("app.email_utils.send_email_now", lambda *a, **k: calls.append(1))

    job = enqueue_job(db_session, "email", {"to": "a@example.com", "subject": "s", "html_body": "b"})
    job.next_attempt_at = utcnow() + timedelta(hours=1)
    db_session.commit()

    processed = run_pending_jobs(db_session)

    assert processed == 0
    assert calls == []
    db_session.refresh(job)
    assert job.status == "pending"
    assert job.attempts == 0


def test_run_pending_jobs_unknown_job_type_fails_without_crashing(db_session):
    job = enqueue_job(db_session, "carrier_pigeon", {}, max_attempts=1)
    processed = run_pending_jobs(db_session)

    assert processed == 1
    db_session.refresh(job)
    assert job.status == "failed"
    assert "desconhecido" in job.last_error


def test_push_job_dispatches_to_send_push_now(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.routes.push.send_push_now",
        lambda app_id, end_user_id, title, body, db: calls.append((app_id, end_user_id, title, body)),
    )

    enqueue_job(db_session, "push", {"app_id": 1, "end_user_id": 2, "title": "Oi", "body": "Mensagem"})
    run_pending_jobs(db_session)

    assert calls == [(1, 2, "Oi", "Mensagem")]


def test_webhook_job_posts_to_url(db_session, monkeypatch):
    calls = []

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def _fake_post(url, json, headers, timeout):
        calls.append((url, json, headers, timeout))
        return _FakeResponse()

    monkeypatch.setattr("httpx.post", _fake_post)

    job = enqueue_job(db_session, "webhook", {"url": "https://example.com/hook", "body": {"event": "test"}})
    run_pending_jobs(db_session)

    assert calls == [("https://example.com/hook", {"event": "test"}, {}, 10.0)]
    db_session.refresh(job)
    assert job.status == "done"


def _published_app(client, register_user, email):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Fila", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_creating_order_enqueues_owner_notification_email(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "jobs1@example.com")

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    )
    assert order.status_code == 201

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").all()
    assert any("Novo pedido" in job.payload["subject"] for job in jobs)


def test_order_status_change_enqueues_email_and_push_for_logged_customer(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "jobs2@example.com")

    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": "clientejobs2@example.com", "password": "senha12345", "full_name": "Cliente"},
    )
    end_user_token = register_end_user.json()["access_token"]

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers={"Authorization": f"Bearer {end_user_token}"},
    )
    order_id = order.json()["id"]

    before = db_session.query(BackgroundJob).count()
    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "confirmed"}, headers=owner_headers)
    after_jobs = db_session.query(BackgroundJob).order_by(BackgroundJob.id).all()[before:]

    job_types = {job.job_type for job in after_jobs}
    assert job_types == {"email", "push"}
    email_job = next(job for job in after_jobs if job.job_type == "email")
    assert email_job.payload["to"] == "clientejobs2@example.com"
    push_job = next(job for job in after_jobs if job.job_type == "push")
    assert push_job.payload["end_user_id"] is not None
