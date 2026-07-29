def _auth_headers(client, register_user, email="versions@example.com"):
    data = register_user(email=email)
    return {"Authorization": f"Bearer {data['access_token']}"}


def _create_app(client, headers, name="App Versionado"):
    response = client.post(
        "/api/apps/",
        json={"name": name, "description": "", "template_type": "other"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_update_creates_version_snapshot_of_previous_state(client, register_user):
    headers = _auth_headers(client, register_user, "snap@example.com")
    app_id = _create_app(client, headers, "Nome Original")

    update = client.put(f"/api/apps/{app_id}", json={"name": "Nome Novo"}, headers=headers)
    assert update.status_code == 200, update.text

    versions = client.get(f"/api/apps/{app_id}/versions", headers=headers)
    assert versions.status_code == 200, versions.text
    body = versions.json()
    assert len(body) == 1
    # a versão salva é o estado ANTES da mudança, não depois
    assert body[0]["name"] == "Nome Original"


def test_status_only_update_does_not_create_version(client, register_user):
    headers = _auth_headers(client, register_user, "statusonly@example.com")
    app_id = _create_app(client, headers)

    update = client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    assert update.status_code == 200, update.text

    versions = client.get(f"/api/apps/{app_id}/versions", headers=headers)
    assert versions.status_code == 200, versions.text
    assert versions.json() == []


def test_restore_version_reverts_content_and_snapshots_current_state(client, register_user):
    headers = _auth_headers(client, register_user, "restore@example.com")
    app_id = _create_app(client, headers, "Nome V1")

    client.put(f"/api/apps/{app_id}", json={"name": "Nome V2"}, headers=headers)
    versions = client.get(f"/api/apps/{app_id}/versions", headers=headers).json()
    assert len(versions) == 1
    v1_id = versions[0]["id"]
    assert versions[0]["name"] == "Nome V1"

    restore = client.post(f"/api/apps/{app_id}/versions/{v1_id}/restore", headers=headers)
    assert restore.status_code == 200, restore.text
    assert restore.json()["name"] == "Nome V1"

    app = client.get(f"/api/apps/{app_id}", headers=headers)
    assert app.json()["name"] == "Nome V1"

    # a restauração também virou uma versão nova (estado "Nome V2" antes de restaurar)
    versions_after = client.get(f"/api/apps/{app_id}/versions", headers=headers).json()
    assert len(versions_after) == 2
    names = {v["name"] for v in versions_after}
    assert names == {"Nome V1", "Nome V2"}


def test_restore_nonexistent_version_returns_404(client, register_user):
    headers = _auth_headers(client, register_user, "missing@example.com")
    app_id = _create_app(client, headers)

    restore = client.post(f"/api/apps/{app_id}/versions/999999/restore", headers=headers)
    assert restore.status_code == 404


def test_versions_are_isolated_per_app_and_owner(client, register_user):
    headers_a = _auth_headers(client, register_user, "owner_a@example.com")
    headers_b = _auth_headers(client, register_user, "owner_b@example.com")
    app_a = _create_app(client, headers_a, "App A")

    client.put(f"/api/apps/{app_a}", json={"name": "App A editado"}, headers=headers_a)

    forbidden = client.get(f"/api/apps/{app_a}/versions", headers=headers_b)
    assert forbidden.status_code == 404


def test_version_history_capped_at_max_versions(client, register_user):
    headers = _auth_headers(client, register_user, "cap@example.com")
    app_id = _create_app(client, headers, "Nome 0")

    for i in range(1, 25):
        response = client.put(f"/api/apps/{app_id}", json={"name": f"Nome {i}"}, headers=headers)
        assert response.status_code == 200, response.text

    versions = client.get(f"/api/apps/{app_id}/versions", headers=headers).json()
    assert len(versions) == 20
