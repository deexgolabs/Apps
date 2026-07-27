import dns.exception

import app.routes.custom_domain as custom_domain_module


def _create_app(client, register_user, email="domain@example.com", name="App Domínio"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": name, "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    return app_id, headers


def _fake_txt_answer(value: str):
    class FakeRdata:
        strings = [value.encode()]

    return [FakeRdata()]


def test_set_custom_domain_returns_verification_instructions(client, register_user):
    app_id, headers = _create_app(client, register_user, "domainset@example.com")

    response = client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "Loja.Exemplo.com.br"}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["domain"] == "loja.exemplo.com.br"
    assert body["verified"] is False
    assert body["verification_host"] == "_deexgo-challenge.loja.exemplo.com.br"
    assert body["verification_token"]


def test_set_custom_domain_rejects_invalid_format(client, register_user):
    app_id, headers = _create_app(client, register_user, "domaininvalid@example.com")

    response = client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "not a domain"}, headers=headers)
    assert response.status_code == 400


def test_set_custom_domain_requires_owner(client, register_user):
    app_id, _ = _create_app(client, register_user, "domainowner1@example.com")
    other = register_user(email="domainowner2@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    response = client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=other_headers)
    assert response.status_code == 404


def test_verify_custom_domain_succeeds_when_txt_matches(client, register_user, db_session, monkeypatch):
    app_id, headers = _create_app(client, register_user, "domainverifyok@example.com")
    set_response = client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers)
    token = set_response.json()["verification_token"]

    monkeypatch.setattr(custom_domain_module.dns.resolver, "resolve", lambda host, rtype, lifetime=10.0: _fake_txt_answer(token))

    response = client.post(f"/api/apps/{app_id}/custom-domain/verify", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verified"] is True
    assert body["verification_token"] is None


def test_verify_custom_domain_fails_when_token_mismatch(client, register_user, monkeypatch):
    app_id, headers = _create_app(client, register_user, "domainverifymismatch@example.com")
    client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers)

    monkeypatch.setattr(custom_domain_module.dns.resolver, "resolve", lambda host, rtype, lifetime=10.0: _fake_txt_answer("token-errado"))

    response = client.post(f"/api/apps/{app_id}/custom-domain/verify", headers=headers)
    assert response.status_code == 400


def test_verify_custom_domain_fails_when_dns_record_missing(client, register_user, monkeypatch):
    app_id, headers = _create_app(client, register_user, "domainverifymissing@example.com")
    client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers)

    def raise_nxdomain(host, rtype, lifetime=10.0):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(custom_domain_module.dns.resolver, "resolve", raise_nxdomain)

    response = client.post(f"/api/apps/{app_id}/custom-domain/verify", headers=headers)
    assert response.status_code == 400


def test_verify_custom_domain_requires_a_pending_domain(client, register_user):
    app_id, headers = _create_app(client, register_user, "domainverifynone@example.com")

    response = client.post(f"/api/apps/{app_id}/custom-domain/verify", headers=headers)
    assert response.status_code == 400


def test_set_custom_domain_conflicts_with_already_verified_domain(client, register_user, monkeypatch):
    app_a, headers_a = _create_app(client, register_user, "domainconflicta@example.com")
    app_b, headers_b = _create_app(client, register_user, "domainconflictb@example.com")

    set_a = client.put(f"/api/apps/{app_a}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers_a)
    token = set_a.json()["verification_token"]
    monkeypatch.setattr(custom_domain_module.dns.resolver, "resolve", lambda host, rtype, lifetime=10.0: _fake_txt_answer(token))
    verify_a = client.post(f"/api/apps/{app_a}/custom-domain/verify", headers=headers_a)
    assert verify_a.json()["verified"] is True

    conflict = client.put(f"/api/apps/{app_b}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers_b)
    assert conflict.status_code == 409


def test_remove_custom_domain_clears_state(client, register_user):
    app_id, headers = _create_app(client, register_user, "domainremove@example.com")
    client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers)

    response = client.delete(f"/api/apps/{app_id}/custom-domain", headers=headers)
    assert response.status_code == 204

    status_response = client.get(f"/api/apps/{app_id}/custom-domain", headers=headers)
    assert status_response.json() == {"domain": None, "verified": False, "verification_host": None, "verification_token": None}


def test_resolve_domain_public_endpoint_returns_app_id_for_verified_published_app(client, register_user, monkeypatch):
    app_id, headers = _create_app(client, register_user, "domainresolve@example.com")
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)

    set_response = client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers)
    token = set_response.json()["verification_token"]
    monkeypatch.setattr(custom_domain_module.dns.resolver, "resolve", lambda host, rtype, lifetime=10.0: _fake_txt_answer(token))
    client.post(f"/api/apps/{app_id}/custom-domain/verify", headers=headers)

    response = client.get("/api/resolve-domain", params={"host": "LOJA.EXEMPLO.COM:443"})
    assert response.status_code == 200
    assert response.json() == {"app_id": app_id}


def test_resolve_domain_returns_404_for_unverified_domain(client, register_user):
    app_id, headers = _create_app(client, register_user, "domainresolveunverified@example.com")
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    client.put(f"/api/apps/{app_id}/custom-domain", json={"domain": "loja.exemplo.com"}, headers=headers)

    response = client.get("/api/resolve-domain", params={"host": "loja.exemplo.com"})
    assert response.status_code == 404


def test_resolve_domain_returns_404_for_unknown_domain(client):
    response = client.get("/api/resolve-domain", params={"host": "naoexiste.exemplo.com"})
    assert response.status_code == 404
