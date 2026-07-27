import io

from app.models import ItemReview, ItemVariation, ModuleItem


def _published_app(client, register_user, email="items@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Itens", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _create_item(client, app_id, headers, name="Pizza", price=30.0):
    response = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items",
        json={"name": name, "price": price},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _register_end_user(client, app_id, email="cliente@example.com"):
    response = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": "Cliente"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def test_variation_crud_ownership_and_limit(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "variations@example.com")
    item_id = _create_item(client, app_id, headers, name="Pizza", price=30.0)

    other = register_user(email="variationsother@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    forbidden = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/variations",
        json={"name": "Grande", "price": 45.0},
        headers=other_headers,
    )
    assert forbidden.status_code == 404

    created = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/variations",
        json={"name": "Grande", "price": 45.0, "stock": 5},
        headers=headers,
    )
    assert created.status_code == 201
    variation_id = created.json()["id"]

    listed = client.get(f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/variations", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/variations/{variation_id}",
        json={"price": 50.0},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 50.0

    deleted = client.delete(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/variations/{variation_id}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert db_session.query(ItemVariation).filter(ItemVariation.id == variation_id).first() is None


def test_public_items_search_filters_by_query_and_category(client, register_user):
    app_id, headers = _published_app(client, register_user, "search@example.com")
    _create_item(client, app_id, headers, name="Pizza Calabresa", price=30.0)
    _create_item(client, app_id, headers, name="Refrigerante Lata", price=6.0)

    all_items = client.get(f"/api/apps/{app_id}/public/modules/catalogo/items")
    assert all_items.status_code == 200
    assert len(all_items.json()) == 2

    filtered = client.get(f"/api/apps/{app_id}/public/modules/catalogo/items", params={"q": "pizza"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["name"] == "Pizza Calabresa"

    none_match = client.get(f"/api/apps/{app_id}/public/modules/catalogo/items", params={"q": "sushi"})
    assert none_match.status_code == 200
    assert len(none_match.json()) == 0


def test_review_requires_login_and_is_upsert_not_duplicate(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "reviews@example.com")
    item_id = _create_item(client, app_id, headers, name="Bolo", price=20.0)
    end_user_token = _register_end_user(client, app_id, "reviewer@example.com")
    end_user_headers = {"Authorization": f"Bearer {end_user_token}"}

    unauthenticated = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/reviews",
        json={"rating": 5, "comment": "Ótimo"},
    )
    assert unauthenticated.status_code == 401

    created = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/reviews",
        json={"rating": 5, "comment": "Ótimo"},
        headers=end_user_headers,
    )
    assert created.status_code == 200
    assert created.json()["rating"] == 5

    updated = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/reviews",
        json={"rating": 3, "comment": "Mudei de ideia"},
        headers=end_user_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["rating"] == 3

    count = db_session.query(ItemReview).filter(ItemReview.item_id == item_id).count()
    assert count == 1

    listed = client.get(f"/api/apps/{app_id}/public/modules/catalogo/items/{item_id}/reviews")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["end_user_name"] == "Cliente"

    items = client.get(f"/api/apps/{app_id}/public/modules/catalogo/items")
    item = next(i for i in items.json() if i["id"] == item_id)
    assert item["avg_rating"] == 3.0
    assert item["review_count"] == 1


def test_export_items_csv_returns_all_fields(client, register_user):
    app_id, headers = _published_app(client, register_user, "exportcsv@example.com")
    category = client.post(
        f"/api/apps/{app_id}/modules/catalogo/categories", json={"name": "Bebidas"}, headers=headers
    )
    category_id = category.json()["id"]
    client.post(
        f"/api/apps/{app_id}/modules/catalogo/items",
        json={"name": "Refrigerante", "description": "Lata 350ml", "price": 6.0, "stock": 20, "category_id": category_id},
        headers=headers,
    )

    response = client.get(f"/api/apps/{app_id}/modules/catalogo/items/export.csv", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    body = response.text
    assert "name,description,price,stock,category,image_url" in body
    assert "Refrigerante,Lata 350ml,6.0,20,Bebidas," in body


def test_export_items_csv_requires_owner(client, register_user):
    app_id, headers = _published_app(client, register_user, "exportcsvowner@example.com")
    other = register_user(email="exportcsvother@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    response = client.get(f"/api/apps/{app_id}/modules/catalogo/items/export.csv", headers=other_headers)
    assert response.status_code == 404


def test_import_items_csv_creates_items_and_categories(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "importcsv@example.com")

    csv_content = (
        "name,description,price,stock,category,image_url\n"
        "Pizza Marguerita,Molho e queijo,35.0,10,Pizzas,\n"
        "Coxinha,,8.5,,Salgados,https://example.com/coxinha.jpg\n"
    )
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/api/apps/{app_id}/modules/catalogo/items/import.csv", headers=headers, files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 2
    assert body["skipped"] == 0

    items = db_session.query(ModuleItem).filter(ModuleItem.app_id == app_id).all()
    assert len(items) == 2
    pizza = next(i for i in items if i.name == "Pizza Marguerita")
    assert pizza.price == 35.0
    assert pizza.stock == 10
    coxinha = next(i for i in items if i.name == "Coxinha")
    assert coxinha.stock is None
    assert coxinha.image_url == "https://example.com/coxinha.jpg"

    categories = client.get(f"/api/apps/{app_id}/modules/catalogo/categories", headers=headers).json()
    assert {c["name"] for c in categories} == {"Pizzas", "Salgados"}


def test_import_items_csv_skips_rows_without_name(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "importcsvskip@example.com")

    csv_content = "name,price\nSanduiche,15.0\n,20.0\n"
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/api/apps/{app_id}/modules/catalogo/items/import.csv", headers=headers, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["skipped"] == 1

    count = db_session.query(ModuleItem).filter(ModuleItem.app_id == app_id).count()
    assert count == 1


def test_import_items_csv_stops_at_plan_limit(client, register_user, db_session):
    from app.models import User

    app_id, headers = _published_app(client, register_user, "importcsvlimit@example.com")
    user = db_session.query(User).filter(User.email == "importcsvlimit@example.com").first()
    user.plan = "free"
    db_session.commit()

    csv_content = "name,price\n" + "".join(f"Item {i},{i}.0\n" for i in range(1, 15))
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(f"/api/apps/{app_id}/modules/catalogo/items/import.csv", headers=headers, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["created"] + body["skipped"] == 14
    assert body["skipped"] > 0
    assert body["message"] is not None
