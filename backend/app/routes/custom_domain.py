import re
import secrets

import dns.exception
import dns.resolver
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access import get_app_for_read, get_app_for_write
from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, User
from app.schemas import CustomDomainRequest, CustomDomainResponse, ResolveDomainResponse

router = APIRouter(prefix="/api/apps/{app_id}/custom-domain", tags=["custom-domain"])
public_router = APIRouter(prefix="/api", tags=["custom-domain"])

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")


def _challenge_host(domain: str) -> str:
    return f"_deexgo-challenge.{domain}"


def _to_response(app: App) -> CustomDomainResponse:
    if not app.custom_domain:
        return CustomDomainResponse()
    return CustomDomainResponse(
        domain=app.custom_domain,
        verified=app.custom_domain_verified,
        verification_host=None if app.custom_domain_verified else _challenge_host(app.custom_domain),
        verification_token=None if app.custom_domain_verified else app.custom_domain_verification_token,
    )


@router.get("", response_model=CustomDomainResponse)
async def get_custom_domain(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = get_app_for_read(app_id, db, current_user)
    return _to_response(app)


@router.put("", response_model=CustomDomainResponse)
async def set_custom_domain(
    app_id: int,
    payload: CustomDomainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra o domínio desejado (ainda não verificado) e gera um token de
    desafio DNS. Trocar de domínio sempre reinicia a verificação — mesmo que
    já tivesse um verificado antes, o novo precisa provar posse de novo."""
    app = get_app_for_write(app_id, db, current_user)

    domain = payload.domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    if not DOMAIN_RE.match(domain):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domínio inválido")

    existing = (
        db.query(App)
        .filter(App.custom_domain == domain, App.id != app_id, App.custom_domain_verified.is_(True))
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esse domínio já está em uso por outro app")

    app.custom_domain = domain
    app.custom_domain_verified = False
    app.custom_domain_verification_token = secrets.token_hex(16)
    db.commit()
    db.refresh(app)
    return _to_response(app)


@router.post("/verify", response_model=CustomDomainResponse)
async def verify_custom_domain(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confere se o registro TXT de desafio foi criado no DNS do domínio.
    Nunca confia em nada que não seja a resposta real do DNS."""
    app = get_app_for_write(app_id, db, current_user)

    if not app.custom_domain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum domínio pendente de verificação")
    if app.custom_domain_verified:
        return _to_response(app)

    challenge_host = _challenge_host(app.custom_domain)
    try:
        answers = dns.resolver.resolve(challenge_host, "TXT", lifetime=10.0)
    except dns.resolver.NXDOMAIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registro TXT não encontrado em {challenge_host}. Confira se o DNS já propagou (pode levar algumas horas).",
        )
    except dns.exception.DNSException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao consultar DNS: {exc}")

    found = any(
        app.custom_domain_verification_token in b"".join(rdata.strings).decode("utf-8", errors="ignore")
        for rdata in answers
    )
    if not found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registro TXT encontrado, mas o valor não confere com o token esperado.",
        )

    app.custom_domain_verified = True
    db.commit()
    db.refresh(app)
    return _to_response(app)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def remove_custom_domain(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = get_app_for_write(app_id, db, current_user)
    app.custom_domain = None
    app.custom_domain_verified = False
    app.custom_domain_verification_token = None
    db.commit()
    return None


@public_router.get("/resolve-domain", response_model=ResolveDomainResponse)
async def resolve_domain(host: str, db: Session = Depends(get_db)):
    """Usado pelo middleware do Next.js: dado o Host de uma requisição, acha
    qual app publicado corresponde a esse domínio próprio verificado. Rota
    pública e sem autenticação — só devolve o app_id, nada sensível."""
    host = host.strip().lower().split(":")[0]
    app = (
        db.query(App)
        .filter(App.custom_domain == host, App.custom_domain_verified.is_(True), App.status == "published")
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domínio não encontrado")
    return ResolveDomainResponse(app_id=app.id)
