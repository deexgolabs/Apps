from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.rate_limit import limiter
from app.routes import auth, users, apps, modules, module_config, module_items, submissions, end_users, payments, public, admin, billing, push, uploads, mercado_livre, oauth, orders, item_variations, reviews
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

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


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
