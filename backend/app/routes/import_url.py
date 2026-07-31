import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access import get_app_for_write
from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, User
from app.schemas import ImportFromUrlRequest, ImportFromUrlResponse

router = APIRouter(prefix="/api/apps/{app_id}/import-from-url", tags=["import-url"])

MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 MB -- só precisamos do <head>, nunca da página inteira


def _assert_public_url(url: str) -> None:
    """Bloqueia SSRF: só permite http(s) pra um host público, nunca IPs
    privados/loopback/link-local (ex: localhost, 127.0.0.1, 169.254.x.x,
    metadados de cloud). Resolve o hostname aqui mesmo pra não confiar em DNS
    que possa reapontar depois da checagem."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A URL precisa começar com http:// ou https://")
    if not parsed.hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL inválida")

    try:
        addrinfo = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível resolver esse endereço")

    for family, _, _, _, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esse endereço não é permitido")


def _extract_meta(html: str, *names: str) -> str | None:
    for name in names:
        match = re.search(
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
            html,
            re.IGNORECASE,
        ) or re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>([^<]*)</title>", html, re.IGNORECASE)
    return match.group(1).strip() if match and match.group(1).strip() else None


@router.post("", response_model=ImportFromUrlResponse)
async def import_from_url(
    app_id: int,
    payload: ImportFromUrlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca a URL informada (site ou página de rede social do dono) e extrai
    nome/descrição/imagem via meta tags Open Graph (og:title, og:description,
    og:image) -- não salva nada sozinho, só devolve os dados pro dono revisar
    e confirmar clicando em Salvar, igual qualquer outra mudança no construtor."""
    get_app_for_write(app_id, db, current_user)

    url = payload.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    _assert_public_url(url)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, max_redirects=3) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mozilla/5.0 (compatible; DeexgoImportBot/1.0)"}) as response:
                _assert_public_url(str(response.url))
                if response.status_code >= 400:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Não foi possível acessar essa URL (HTTP {response.status_code})")
                chunks = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_BODY_BYTES:
                        break
                    chunks.append(chunk)
                html = b"".join(chunks).decode("utf-8", errors="ignore")
                final_url = str(response.url)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Não foi possível acessar essa URL: {exc}")

    name = _extract_meta(html, "og:title", "twitter:title") or _extract_title(html)
    description = _extract_meta(html, "og:description", "twitter:description", "description")
    image_url = _extract_meta(html, "og:image", "twitter:image")
    if image_url:
        image_url = urljoin(final_url, image_url)

    if not name and not description and not image_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não encontramos informações aproveitáveis nessa URL")

    return ImportFromUrlResponse(name=name, description=description, image_url=image_url)
