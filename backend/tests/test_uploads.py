import io

from PIL import Image


def _auth_headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def _png_bytes(width, height, mode="RGB", color=(255, 0, 0)):
    image = Image.new(mode, (width, height), color)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _gif_bytes(width=10, height=10):
    image = Image.new("RGB", (width, height), (0, 255, 0))
    buf = io.BytesIO()
    image.save(buf, format="GIF")
    return buf.getvalue()


def test_upload_resizes_oversized_image(client, register_user):
    data = register_user(email="upload1@example.com")
    headers = _auth_headers(data)

    big_png = _png_bytes(3000, 2000)
    response = client.post(
        "/api/uploads/image",
        files={"file": ("big.png", big_png, "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    url = response.json()["url"]
    filename = url.rsplit("/", 1)[-1]

    from app.routes.uploads import UPLOAD_DIR

    saved_bytes = (UPLOAD_DIR / filename).read_bytes()
    saved_image = Image.open(io.BytesIO(saved_bytes))
    assert max(saved_image.width, saved_image.height) <= 1920
    assert len(saved_bytes) < len(big_png)


def test_upload_small_image_is_not_upscaled(client, register_user):
    data = register_user(email="upload2@example.com")
    headers = _auth_headers(data)

    small_png = _png_bytes(50, 40)
    response = client.post(
        "/api/uploads/image",
        files={"file": ("small.png", small_png, "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    url = response.json()["url"]
    filename = url.rsplit("/", 1)[-1]

    from app.routes.uploads import UPLOAD_DIR

    saved_image = Image.open(io.BytesIO((UPLOAD_DIR / filename).read_bytes()))
    assert (saved_image.width, saved_image.height) == (50, 40)


def test_upload_png_with_transparency_keeps_alpha(client, register_user):
    data = register_user(email="upload3@example.com")
    headers = _auth_headers(data)

    rgba_png = _png_bytes(2500, 100, mode="RGBA", color=(0, 0, 255, 128))
    response = client.post(
        "/api/uploads/image",
        files={"file": ("alpha.png", rgba_png, "image/png")},
        headers=headers,
    )
    assert response.status_code == 200
    url = response.json()["url"]
    filename = url.rsplit("/", 1)[-1]

    from app.routes.uploads import UPLOAD_DIR

    saved_image = Image.open(io.BytesIO((UPLOAD_DIR / filename).read_bytes()))
    assert saved_image.mode in ("RGBA", "LA")
    assert max(saved_image.width, saved_image.height) <= 1920


def test_upload_gif_is_stored_unchanged(client, register_user):
    data = register_user(email="upload4@example.com")
    headers = _auth_headers(data)

    gif = _gif_bytes()
    response = client.post(
        "/api/uploads/image",
        files={"file": ("anim.gif", gif, "image/gif")},
        headers=headers,
    )
    assert response.status_code == 200
    url = response.json()["url"]
    filename = url.rsplit("/", 1)[-1]

    from app.routes.uploads import UPLOAD_DIR

    assert (UPLOAD_DIR / filename).read_bytes() == gif


def test_upload_rejects_oversized_file(client, register_user):
    data = register_user(email="upload5@example.com")
    headers = _auth_headers(data)

    huge = b"\x00" * (6 * 1024 * 1024)
    response = client.post(
        "/api/uploads/image",
        files={"file": ("huge.png", huge, "image/png")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_rejects_unsupported_content_type(client, register_user):
    data = register_user(email="upload6@example.com")
    headers = _auth_headers(data)

    response = client.post(
        "/api/uploads/image",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_requires_auth(client):
    png = _png_bytes(10, 10)
    response = client.post(
        "/api/uploads/image",
        files={"file": ("x.png", png, "image/png")},
    )
    assert response.status_code == 401
