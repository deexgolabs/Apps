from app.models import User


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
