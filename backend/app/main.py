import asyncio
import logging
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.rate_limit import limiter
from app.routes import auth, users, apps, modules, module_config, module_items, submissions, end_users, payments, public, admin, billing, push, uploads, mercado_livre, oauth, orders, item_variations, reviews, coupons, loyalty, wishlist, webhooks, custom_domain, import_url, audit_logs, collaborators, reservations, cart_tracking, campaigns, auto_coupons
from app.seed import seed_modules, seed_plan_configs

# Sem DSN (padrão), sentry_sdk.init vira um no-op — nada é enviado nem
# processado. Defina SENTRY_DSN no .env pra ativar de verdade.
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1, send_default_pii=False)

# Schema do banco é responsabilidade do Alembic (`alembic upgrade head`), não do app subindo.

# Popular módulos e planos padrão (idempotente)
seed_modules()
seed_plan_configs()

# Criar app
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MVP de plataforma de criação de aplicativos"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(apps.router)
app.include_router(modules.router)
app.include_router(module_config.router)
app.include_router(module_items.router)
app.include_router(submissions.router)
app.include_router(end_users.router)
app.include_router(payments.router)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(push.router)
app.include_router(uploads.router)
app.include_router(mercado_livre.router)
app.include_router(oauth.router)
app.include_router(orders.router)
app.include_router(item_variations.router)
app.include_router(reviews.router)
app.include_router(coupons.router)
app.include_router(loyalty.router)
app.include_router(wishlist.router)
app.include_router(webhooks.router)
app.include_router(custom_domain.router)
app.include_router(custom_domain.public_router)
app.include_router(import_url.router)
app.include_router(audit_logs.router)
app.include_router(collaborators.router)
app.include_router(reservations.router)
app.include_router(cart_tracking.router)
app.include_router(campaigns.router)
app.include_router(auto_coupons.router)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

BACKGROUND_WORKER_INTERVAL_SECONDS = 15
_worker_logger = logging.getLogger("app.jobs.worker")


async def _background_job_worker() -> None:
    """Processa a fila de background (e-mail/push/webhook) em loop, dentro do
    próprio processo do backend -- ver app/jobs.py. Cada iteração abre sua
    própria sessão de banco, isolada da requisição HTTP que a originou."""
    from app.database import SessionLocal
    from app.jobs import run_pending_jobs
    from app.abandoned_cart import send_abandoned_cart_reminders
    from app.auto_coupons import send_birthday_coupons

    while True:
        try:
            db = SessionLocal()
            try:
                run_pending_jobs(db)
                send_abandoned_cart_reminders(db)
                send_birthday_coupons(db)
            finally:
                db.close()
        except Exception:
            _worker_logger.exception("Erro no worker da fila de background")
        await asyncio.sleep(BACKGROUND_WORKER_INTERVAL_SECONDS)


@app.on_event("startup")
async def _start_background_worker() -> None:
    app.state.background_worker_task = asyncio.create_task(_background_job_worker())


@app.on_event("shutdown")
async def _stop_background_worker() -> None:
    task = getattr(app.state, "background_worker_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/")
async def root():
    return {
        "message": f"{settings.app_name} API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
