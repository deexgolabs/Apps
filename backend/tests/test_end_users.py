def _published_app(client, register_user, email="lojista@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Perfil", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _register_end_user(client, app_id, email="cliente@example.com", password="senha12345"):
    response = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": password, "full_name": "Cliente Teste"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_update_profile_sets_phone_and_address(client, register_user):
    app_id, _ = _published_app(client, register_user)
    token = _register_end_user(client, app_id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        f"/api/apps/{app_id}/end-users/me",
        json={"phone": "11999998888", "address": "Rua das Flores, 123"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "11999998888"
    assert body["address"] == "Rua das Flores, 123"

    me = client.get(f"/api/apps/{app_id}/end-users/me", headers=headers)
    assert me.json()["phone"] == "11999998888"


def test_update_profile_changes_password_with_correct_current_password(client, register_user):
    app_id, _ = _published_app(client, register_user, "lojista2@example.com")
    token = _register_end_user(client, app_id, "cliente2@example.com", "senhaAntiga1")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        f"/api/apps/{app_id}/end-users/me",
        json={"current_password": "senhaAntiga1", "new_password": "senhaNova1"},
        headers=headers,
    )
    assert response.status_code == 200

    login = client.post(
        f"/api/apps/{app_id}/end-users/login",
        json={"email": "cliente2@example.com", "password": "senhaNova1"},
    )
    assert login.status_code == 200


def test_update_profile_rejects_wrong_current_password(client, register_user):
    app_id, _ = _published_app(client, register_user, "lojista3@example.com")
    token = _register_end_user(client, app_id, "cliente3@example.com", "senhaCerta1")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        f"/api/apps/{app_id}/end-users/me",
        json={"current_password": "senhaErrada", "new_password": "novaSenha1"},
        headers=headers,
    )
    assert response.status_code == 400


def test_update_profile_requires_auth(client, register_user):
    app_id, _ = _published_app(client, register_user, "lojista4@example.com")

    response = client.put(
        f"/api/apps/{app_id}/end-users/me",
        json={"phone": "11999998888"},
    )
    assert response.status_code == 401
