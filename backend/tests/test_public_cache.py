def _auth_headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def _published_app(client, register_user, email):
    data = register_user(email=email)
    headers = _auth_headers(data)
    create = client.post(
        "/api/apps/",
        json={"name": "App Cache", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_public_app_includes_description(client, register_user):
    data = register_user(email="cache_desc@example.com")
    headers = _auth_headers(data)
    create = client.post(
        "/api/apps/",
        json={"name": "App Com Descrição", "description": "Comida boa e rápida", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)

    response = client.get(f"/api/apps/{app_id}/public")
    assert response.json()["description"] == "Comida boa e rápida"


def test_public_app_reflects_update_after_cache_invalidation(client, register_user):
    app_id, headers = _published_app(client, register_user, "cache1@example.com")

    first = client.get(f"/api/apps/{app_id}/public")
    assert first.status_code == 200
    assert first.json()["name"] == "App Cache"

    client.put(f"/api/apps/{app_id}", json={"name": "App Cache Renomeado"}, headers=headers)

    second = client.get(f"/api/apps/{app_id}/public")
    assert second.json()["name"] == "App Cache Renomeado"


def test_public_app_is_served_from_cache_on_repeated_reads(client, register_user, monkeypatch):
    app_id, headers = _published_app(client, register_user, "cache2@example.com")

    client.get(f"/api/apps/{app_id}/public")

    from app.public_utils import get_published_app as real_get_published_app
    import app.routes.public as public_module

    calls = {"count": 0}

    def _spy(*args, **kwargs):
        calls["count"] += 1
        return real_get_published_app(*args, **kwargs)

    monkeypatch.setattr(public_module, "get_published_app", _spy)

    client.get(f"/api/apps/{app_id}/public")
    client.get(f"/api/apps/{app_id}/public")

    assert calls["count"] == 0  # nem chega a consultar o banco -- respondeu direto do cache


def test_public_module_config_reflects_update_after_invalidation(client, register_user):
    app_id, headers = _published_app(client, register_user, "cache3@example.com")

    client.get(f"/api/apps/{app_id}/public/module-configs")
    client.put(
        f"/api/apps/{app_id}/module-config/cardapio",
        json={"settings": {"cor": "azul"}},
        headers=headers,
    )

    response = client.get(f"/api/apps/{app_id}/public/module-configs")
    assert response.json()["cardapio"]["cor"] == "azul"


def test_public_items_reflect_new_item_after_invalidation(client, register_user):
    app_id, headers = _published_app(client, register_user, "cache4@example.com")

    empty = client.get(f"/api/apps/{app_id}/public/modules/cardapio/items")
    assert empty.json() == []

    client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Pizza", "price": 30.0},
        headers=headers,
    )

    response = client.get(f"/api/apps/{app_id}/public/modules/cardapio/items")
    names = [item["name"] for item in response.json()]
    assert names == ["Pizza"]


def test_public_items_reflect_deletion_after_invalidation(client, register_user):
    app_id, headers = _published_app(client, register_user, "cache5@example.com")

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Pizza", "price": 30.0},
        headers=headers,
    )
    item_id = item.json()["id"]
    client.get(f"/api/apps/{app_id}/public/modules/cardapio/items")

    client.delete(f"/api/apps/{app_id}/modules/cardapio/items/{item_id}", headers=headers)

    response = client.get(f"/api/apps/{app_id}/public/modules/cardapio/items")
    assert response.json() == []


def test_public_categories_reflect_new_category_after_invalidation(client, register_user):
    app_id, headers = _published_app(client, register_user, "cache6@example.com")

    empty = client.get(f"/api/apps/{app_id}/public/modules/cardapio/categories")
    assert empty.json() == []

    client.post(
        f"/api/apps/{app_id}/modules/cardapio/categories",
        json={"name": "Bebidas", "order": 0},
        headers=headers,
    )

    response = client.get(f"/api/apps/{app_id}/public/modules/cardapio/categories")
    names = [c["name"] for c in response.json()]
    assert names == ["Bebidas"]


def test_public_cache_is_isolated_per_app(client, register_user):
    app_id_a, headers_a = _published_app(client, register_user, "cache7a@example.com")
    app_id_b, headers_b = _published_app(client, register_user, "cache7b@example.com")

    client.put(f"/api/apps/{app_id_a}", json={"name": "Só o A mudou"}, headers=headers_a)

    response_a = client.get(f"/api/apps/{app_id_a}/public")
    response_b = client.get(f"/api/apps/{app_id_b}/public")
    assert response_a.json()["name"] == "Só o A mudou"
    assert response_b.json()["name"] == "App Cache"
