import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.routes.end_users import FACEBOOK_OAUTH_VERSION, get_or_create_facebook_end_user
from app.utils import create_access_token

router = APIRouter(prefix="/api/end-users", tags=["oauth"])


@router.get("/facebook/callback")
async def facebook_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Callback fixo do OAuth do Facebook — o app_id vem no `state`, já que o
    redirect URI registrado no Facebook precisa ser um único caminho estático
    (um App do Facebook atende todos os apps criados na plataforma)."""
    try:
        app_id = int(state)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="state inválido")

    redirect_uri = f"{settings.backend_url}/api/end-users/facebook/callback"

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.get(
            f"https://graph.facebook.com/{FACEBOOK_OAUTH_VERSION}/oauth/access_token",
            params={
                "client_id": settings.facebook_app_id,
                "redirect_uri": redirect_uri,
                "client_secret": settings.facebook_app_secret,
                "code": code,
            },
        )
        if token_response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro de autenticação do Facebook: {token_response.text}")

        access_token = token_response.json().get("access_token")

        profile_response = await client.get(
            "https://graph.facebook.com/me",
            params={"fields": "id,name,email", "access_token": access_token},
        )
        if profile_response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao buscar perfil do Facebook: {profile_response.text}")

        profile = profile_response.json()

    facebook_id = profile.get("id")
    email = profile.get("email") or f"{facebook_id}@facebook.local"
    full_name = profile.get("name") or "Usuário Facebook"

    end_user = get_or_create_facebook_end_user(app_id, facebook_id, email, full_name, db)

    end_user_token = create_access_token(data={"end_user_id": end_user.id, "app_id": app_id, "type": "end_user"})

    return RedirectResponse(url=f"{settings.frontend_url}/app/{app_id}?fb_token={end_user_token}")
