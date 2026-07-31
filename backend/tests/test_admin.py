from app.models import Order, User


def _make_admin(client, register_user, db_session, email):
    data = register_user(email=email)
    user = db_session.query(User).filter(User.email == email).first()
    user.is_admin = True
    db_session.commit()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_admin_routes_forbidden_for_regular_user(client, register_user):
    data = register_user(email="regular@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    response = client.get("/api/admin/users", headers=headers)
    assert response.status_code == 403


def test_admin_routes_allowed_for_admin_user(client, register_user, db_session):
    data = register_user(email="admin@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    user.is_admin = True
    db_session.commit()

    response = client.get("/api/admin/users", headers=headers)
    assert response.status_code == 200
    assert any(u["email"] == "admin@example.com" for u in response.json())

    apps_response = client.get("/api/admin/apps", headers=headers)
    assert apps_response.status_code == 200


def test_admin_can_update_another_users_plan(client, register_user, db_session):
    admin_data = register_user(email="admin2@example.com")
    target_data = register_user(email="target@example.com")

    admin_user = db_session.query(User).filter(User.email == "admin2@example.com").first()
    admin_user.is_admin = True
    db_session.commit()

    headers = {"Authorization": f"Bearer {admin_data['access_token']}"}
    target_id = target_data["user"]["id"]

    response = client.put(f"/api/admin/users/{target_id}", json={"plan": "business"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["plan"] == "business"


def test_admin_plan_grant_clears_old_expiration(client, register_user, db_session):
    """Concessão manual do admin não deve expirar sozinha por causa de um
    plan_expires_at deixado por uma assinatura paga anterior."""
    from datetime import timedelta
    from app.models import utcnow

    admin_data = register_user(email="admin3@example.com")
    target_data = register_user(email="target2@example.com")

    admin_user = db_session.query(User).filter(User.email == "admin3@example.com").first()
    admin_user.is_admin = True
    db_session.commit()

    target_user = db_session.query(User).filter(User.email == "target2@example.com").first()
    target_user.plan_expires_at = utcnow() - timedelta(days=1)
    db_session.commit()

    headers = {"Authorization": f"Bearer {admin_data['access_token']}"}
    target_id = target_data["user"]["id"]

    response = client.put(f"/api/admin/users/{target_id}", json={"plan": "business"}, headers=headers)
    assert response.status_code == 200

    target_headers = {"Authorization": f"Bearer {target_data['access_token']}"}
    me = client.get("/api/users/me", headers=target_headers)
    assert me.json()["plan"] == "business"
    assert me.json()["plan_expires_at"] is None


def test_admin_can_list_and_edit_plans(client, register_user, db_session):
    headers = _make_admin(client, register_user, db_session, "planadmin@example.com")

    listed = client.get("/api/admin/plans", headers=headers)
    assert listed.status_code == 200
    plans = {p["plan_name"]: p for p in listed.json()}
    assert set(plans) == {"free", "pro", "business"}
    assert plans["pro"]["max_apps"] == 3

    updated = client.put("/api/admin/plans/pro", json={"max_apps": 7, "price": 39.9}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["max_apps"] == 7
    assert updated.json()["price"] == 39.9


def test_updated_plan_limit_is_enforced_on_app_creation(client, register_user, db_session):
    admin_headers = _make_admin(client, register_user, db_session, "planenforce_admin@example.com")
    client.put("/api/admin/plans/free", json={"max_apps": 0}, headers=admin_headers)

    user_data = register_user(email="planenforce_user@example.com")
    user_headers = {"Authorization": f"Bearer {user_data['access_token']}"}

    response = client.post(
        "/api/apps/",
        json={"name": "Deveria falhar", "description": "", "template_type": "other"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_admin_app_detail_suspend_and_delete(client, register_user, db_session):
    admin_headers = _make_admin(client, register_user, db_session, "appadmin@example.com")
    owner_data = register_user(email="appowner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_data['access_token']}"}

    create = client.post(
        "/api/apps/",
        json={"name": "App do dono", "description": "", "template_type": "other"},
        headers=owner_headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=owner_headers)

    order_created = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "teste"}},
    )
    assert order_created.status_code == 201

    detail = client.get(f"/api/admin/apps/{app_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["owner_email"] == "appowner@example.com"

    suspend = client.put(f"/api/admin/apps/{app_id}/status", json={"status": "suspended"}, headers=admin_headers)
    assert suspend.status_code == 200
    assert suspend.json()["status"] == "suspended"

    public_check = client.get(f"/api/apps/{app_id}/public")
    assert public_check.status_code == 404

    delete = client.delete(f"/api/admin/apps/{app_id}", headers=admin_headers)
    assert delete.status_code == 204

    gone = db_session.query(Order).filter(Order.app_id == app_id).count()
    assert gone == 0

    audit = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()]
    assert "update_app_status" in actions
    assert "delete_app" in actions


def test_admin_stats(client, register_user, db_session):
    headers = _make_admin(client, register_user, db_session, "statsadmin@example.com")

    response = client.get("/api/admin/stats", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "mrr" in body
    assert "published_apps" in body
    assert "users_by_plan" in body
