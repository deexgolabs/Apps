from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routes import auth, users, apps, modules, module_config, module_items, submissions, end_users, payments, public, admin, billing, push, uploads, mercado_livre, oauth
from app.seed import seed_modules

# Schema do banco é responsabilidade do Alembic (`alembic upgrade head`), não do app subindo.

# Popular módulos padrão (idempotente)
seed_modules()

# Criar app
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MVP de plataforma de criação de aplicativos"
)

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
