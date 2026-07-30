from app.constants import APP_TEMPLATES


def _auth_headers(client, register_user, email="apps@example.com"):
    data = register_user(email=email)
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_create_app_applies_template_defaults(client, register_user):
    headers = _auth_headers(client, register_user, "template@example.com")
    response = client.post(
        "/api/apps/",
        json={"name": "Restaurante Teste", "description": "", "template_type": "restaurant"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    template = APP_TEMPLATES["restaurant"]
    assert data["config"] == template["config"]
    assert data["modules"] == template["modules"]


def test_update_app_respects_module_plan_limit(client, register_user):
    headers = _auth_headers(client, register_user, "limit@example.com")
    create_response = client.post(
        "/api/apps/",
        json={"name": "App Free", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create_response.json()["id"]

    # plano free permite 5 módulos (PLAN_LIMITS["free"]["modules"])
    too_many_modules = ["texto", "quem_somos", "video", "whatsapp", "mapa", "rss"]
    response = client.put(
        f"/api/apps/{app_id}",
        json={"modules": too_many_modules},
        headers=headers,
    )
    assert response.status_code == 403


def test_second_app_blocked_by_plan_limit(client, register_user):
    headers = _auth_headers(client, register_user, "second@example.com")
    first = client.post(
        "/api/apps/",
        json={"name": "App 1", "description": "", "template_type": "other"},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/apps/",
        json={"name": "App 2", "description": "", "template_type": "other"},
        headers=headers,
    )
    assert second.status_code == 403


def test_create_app_accepts_client_fields(client, register_user):
    headers = _auth_headers(client, register_user, "agencycreate@example.com")
    response = client.post(
        "/api/apps/",
        json={
            "name": "App do Cliente",
            "description": "",
            "template_type": "other",
            "client_name": "Padaria da Esquina",
            "client_email": "contato@padaria.example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["client_name"] == "Padaria da Esquina"
    assert data["client_email"] == "contato@padaria.example.com"


def test_update_app_sets_and_clears_client_fields(client, register_user, db_session):
    from app.models import App

    headers = _auth_headers(client, register_user, "agencyupdate@example.com")
    create_response = client.post(
        "/api/apps/",
        json={"name": "App Agência", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create_response.json()["id"]

    set_response = client.put(
        f"/api/apps/{app_id}",
        json={"client_name": "Salão Bela Vista", "client_email": "dono@salao.example.com"},
        headers=headers,
    )
    assert set_response.status_code == 200
    assert set_response.json()["client_name"] == "Salão Bela Vista"
    assert set_response.json()["client_email"] == "dono@salao.example.com"

    db_app = db_session.query(App).filter(App.id == app_id).first()
    assert db_app.client_name == "Salão Bela Vista"

    # atualização parcial (só name) não deve apagar client_name já salvo —
    # o schema usa Optional[None]=default, então omitir o campo no PUT deve
    # preservar o valor atual (comportamento "not None" já usado por outros campos).
    partial_response = client.put(
        f"/api/apps/{app_id}",
        json={"name": "App Agência Renomeado"},
        headers=headers,
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["client_name"] == "Salão Bela Vista"
