import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from PIL import Image, ImageOps

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
MAX_DIMENSION = 1920  # lado maior, em pixels -- de sobra pra logo, capa ou item de catálogo
JPEG_WEBP_QUALITY = 85

_PIL_FORMATS = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP"}


def _optimize_image(contents: bytes, extension: str) -> bytes:
    """Redimensiona (lado maior até MAX_DIMENSION) e recomprime a imagem antes
    de salvar, removendo metadata EXIF (privacidade + tamanho) no processo --
    sempre aplicando a orientação EXIF antes de descartá-la, senão fotos
    tiradas de celular ficam rotacionadas. GIF fica de fora: redimensionar via
    Pillow perde a animação sem tratamento frame-a-frame, o que não vale a
    complexidade pra um upload de imagem da plataforma (logo/capa/item)."""
    if extension == "gif":
        return contents

    image = Image.open(io.BytesIO(contents))
    image = ImageOps.exif_transpose(image)

    if image.width > MAX_DIMENSION or image.height > MAX_DIMENSION:
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    pil_format = _PIL_FORMATS[extension]
    save_kwargs = {"optimize": True}

    if pil_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
        # JPEG não suporta transparência -- compõe sobre fundo branco em vez de
        # deixar o Pillow descartar o canal alpha (que gera artefatos pretos).
        rgba = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    elif pil_format == "JPEG":
        image = image.convert("RGB")

    if pil_format != "PNG":
        save_kwargs["quality"] = JPEG_WEBP_QUALITY

    output = io.BytesIO()
    image.save(output, format=pil_format, **save_kwargs)
    optimized = output.getvalue()
    # Só usa a versão otimizada se ela realmente ficou menor -- uma imagem já
    # pequena ou bem comprimida pode até crescer um pouco ao recodificar.
    return optimized if len(optimized) < len(contents) else contents


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

    try:
        contents = _optimize_image(contents, extension)
    except Exception:
        # Imagem corrompida ou num formato que o Pillow não decodifica apesar
        # do content-type declarado -- ainda assim salva o arquivo original,
        # já que otimização é um bônus e não deve bloquear o upload.
        pass

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
