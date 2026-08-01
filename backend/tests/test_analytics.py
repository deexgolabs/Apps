from app.models import PageView


def _published_app(client, register_user, email="analytics@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Analytics", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_track_pageview_requires_published_app(client, register_user):
    data = register_user(email="analyticsdraft@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Draft", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    response = client.post(f"/api/apps/{app_id}/analytics/pageview", json={"visitor_hash": "abc"})
    assert response.status_code == 404


def test_track_pageview_persists_row(client, register_user, db_session):
    app_id, _ = _published_app(client, register_user, "analyticstrack@example.com")

    response = client.post(
        f"/api/apps/{app_id}/analytics/pageview",
        json={"module_name": "cardapio", "visitor_hash": "visitor-1"},
    )
    assert response.status_code == 204

    view = db_session.query(PageView).filter(PageView.app_id == app_id).first()
    assert view is not None
    assert view.module_name == "cardapio"
    assert view.visitor_hash == "visitor-1"


def test_analytics_summary_requires_access(client, register_user):
    app_id, _ = _published_app(client, register_user, "analyticsaccess@example.com")
    stranger = register_user(email="analyticsstranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    response = client.get(f"/api/apps/{app_id}/analytics/summary", headers=stranger_headers)
    assert response.status_code == 404


def test_analytics_summary_aggregates_views_and_visitors(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "analyticssummary@example.com")

    client.post(f"/api/apps/{app_id}/analytics/pageview", json={"module_name": "cardapio", "visitor_hash": "v1"})
    client.post(f"/api/apps/{app_id}/analytics/pageview", json={"module_name": "cardapio", "visitor_hash": "v1"})
    client.post(f"/api/apps/{app_id}/analytics/pageview", json={"module_name": "cardapio", "visitor_hash": "v2"})
    client.post(f"/api/apps/{app_id}/analytics/pageview", json={"module_name": "quem_somos", "visitor_hash": "v2"})
    client.post(f"/api/apps/{app_id}/analytics/pageview", json={"visitor_hash": "v3"})

    response = client.get(f"/api/apps/{app_id}/analytics/summary", headers=owner_headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total_views"] == 5
    assert data["unique_visitors"] == 3
    modules_by_name = {m["module_name"]: m["views"] for m in data["top_modules"]}
    assert modules_by_name == {"cardapio": 3, "quem_somos": 1}


def test_analytics_summary_isolated_per_app(client, register_user):
    app_a, owner_a_headers = _published_app(client, register_user, "analyticsappa@example.com")
    app_b, _ = _published_app(client, register_user, "analyticsappb@example.com")

    client.post(f"/api/apps/{app_a}/analytics/pageview", json={"visitor_hash": "v1"})
    client.post(f"/api/apps/{app_b}/analytics/pageview", json={"visitor_hash": "v1"})
    client.post(f"/api/apps/{app_b}/analytics/pageview", json={"visitor_hash": "v2"})

    response = client.get(f"/api/apps/{app_a}/analytics/summary", headers=owner_a_headers)
    assert response.status_code == 200
    assert response.json()["total_views"] == 1
