def _create_app(client, register_user, email="public@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    response = client.post(
        "/api/apps/",
        json={"name": "App Público", "description": "", "template_type": "other"},
        headers=headers,
    )
    return response.json()["id"], headers


def test_public_endpoint_404_while_draft(client, register_user):
    app_id, _ = _create_app(client, register_user)
    response = client.get(f"/api/apps/{app_id}/public")
    assert response.status_code == 404


def test_public_endpoint_200_after_publish(client, register_user):
    app_id, headers = _create_app(client, register_user, "public2@example.com")
    publish = client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    assert publish.status_code == 200

    response = client.get(f"/api/apps/{app_id}/public")
    assert response.status_code == 200
    assert response.json()["id"] == app_id
