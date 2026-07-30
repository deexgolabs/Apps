import socket

import httpx

from app.routes import import_url as import_url_module


def _patch_dns_to_public_ip(monkeypatch):
    """Evita depender de DNS de verdade nos testes -- resolve qualquer host
    pro IP público do Cloudflare DNS (1.1.1.1), inequivocamente roteável
    (as faixas de documentação tipo 203.0.113.0/24 contam como is_private
    no módulo ipaddress do Python, então não servem aqui)."""
    monkeypatch.setattr(
        import_url_module.socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0))],
    )


def _auth_headers(client, register_user, email="import@example.com"):
    data = register_user(email=email)
    return {"Authorization": f"Bearer {data['access_token']}"}


def _create_app(client, headers, name="App Import"):
    response = client.post(
        "/api/apps/",
        json={"name": name, "description": "", "template_type": "other"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


FAKE_HTML = """
<html><head>
<title>Titulo da pagina</title>
<meta property="og:title" content="Minha Loja" />
<meta property="og:description" content="A melhor loja da regiao" />
<meta property="og:image" content="/images/logo.png" />
</head><body></body></html>
"""


class _FakeResponse:
    def __init__(self, html: str, status_code: int = 200, url: str = "https://exemplo.com/"):
        self._html = html.encode("utf-8")
        self.status_code = status_code
        self.url = url

    async def aiter_bytes(self):
        yield self._html


class _FakeStreamContext:
    def __init__(self, response: _FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc):
        return False


class _FakeAsyncClient:
    def __init__(self, html=FAKE_HTML, status_code=200, url="https://exemplo.com/", raise_error=None, **kwargs):
        self._html = html
        self._status_code = status_code
        self._url = url
        self._raise_error = raise_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def stream(self, method, url, **kwargs):
        if self._raise_error:
            raise self._raise_error
        return _FakeStreamContext(_FakeResponse(self._html, self._status_code, self._url))


def _patch_client(monkeypatch, **kwargs):
    monkeypatch.setattr(import_url_module.httpx, "AsyncClient", lambda **_: _FakeAsyncClient(**kwargs))


def test_import_from_url_extracts_og_tags(client, register_user, monkeypatch):
    headers = _auth_headers(client, register_user)
    app_id = _create_app(client, headers)
    _patch_dns_to_public_ip(monkeypatch)
    _patch_client(monkeypatch)

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "https://exemplo.com"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Minha Loja"
    assert data["description"] == "A melhor loja da regiao"
    assert data["image_url"] == "https://exemplo.com/images/logo.png"


def test_import_from_url_falls_back_to_title_tag(client, register_user, monkeypatch):
    headers = _auth_headers(client, register_user, "import2@example.com")
    app_id = _create_app(client, headers)
    html = "<html><head><title>So o titulo</title></head></html>"
    _patch_dns_to_public_ip(monkeypatch)
    _patch_client(monkeypatch, html=html)

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "https://exemplo.com"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "So o titulo"


def test_import_from_url_rejects_private_ip(client, register_user):
    headers = _auth_headers(client, register_user, "import3@example.com")
    app_id = _create_app(client, headers)

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "http://127.0.0.1:8000/secret"},
        headers=headers,
    )
    assert response.status_code == 400


def test_import_from_url_rejects_localhost_hostname(client, register_user):
    headers = _auth_headers(client, register_user, "import4@example.com")
    app_id = _create_app(client, headers)

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "http://localhost/whatever"},
        headers=headers,
    )
    assert response.status_code == 400


def test_import_from_url_rejects_non_http_scheme(client, register_user):
    headers = _auth_headers(client, register_user, "import5@example.com")
    app_id = _create_app(client, headers)

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "ftp://exemplo.com/file"},
        headers=headers,
    )
    assert response.status_code == 400


def test_import_from_url_requires_ownership(client, register_user):
    headers_a = _auth_headers(client, register_user, "import_owner@example.com")
    headers_b = _auth_headers(client, register_user, "import_other@example.com")
    app_id = _create_app(client, headers_a)

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "https://exemplo.com"},
        headers=headers_b,
    )
    assert response.status_code == 404


def test_import_from_url_handles_upstream_error(client, register_user, monkeypatch):
    headers = _auth_headers(client, register_user, "import6@example.com")
    app_id = _create_app(client, headers)
    _patch_dns_to_public_ip(monkeypatch)
    _patch_client(monkeypatch, raise_error=httpx.ConnectError("boom"))

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "https://exemplo.com"},
        headers=headers,
    )
    assert response.status_code == 400


def test_import_from_url_no_usable_data(client, register_user, monkeypatch):
    headers = _auth_headers(client, register_user, "import7@example.com")
    app_id = _create_app(client, headers)
    _patch_dns_to_public_ip(monkeypatch)
    _patch_client(monkeypatch, html="<html><head></head><body>nada aqui</body></html>")

    response = client.post(
        f"/api/apps/{app_id}/import-from-url",
        json={"url": "https://exemplo.com"},
        headers=headers,
    )
    assert response.status_code == 400
