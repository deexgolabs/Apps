import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/image")
async def upload_image(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    extension = ALLOWED_CONTENT_TYPES.get(file.content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem não suportado. Use PNG, JPEG, WEBP ou GIF.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagem muito grande (máximo 5MB).",
        )

    filename = f"{uuid.uuid4().hex}.{extension}"
    (UPLOAD_DIR / filename).write_bytes(contents)

    # Deriva a URL do próprio request (não de uma env var fixa) — assim a URL
    # salva sempre bate com o host real que serviu a requisição, mesmo que
    # BACKEND_URL não esteja configurada corretamente em produção. Lê os
    # headers X-Forwarded-* direto (em vez de request.url) porque esses só
    # refletem o proxy se uvicorn rodar com --proxy-headers, o que não
    # podemos garantir estar ativo no ambiente de deploy.
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return {"url": f"{scheme}://{host}/uploads/{filename}"}
