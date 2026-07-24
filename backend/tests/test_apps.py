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
