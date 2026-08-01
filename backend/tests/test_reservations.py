from datetime import datetime, timedelta, timezone

from app.models import TableReservation


def _published_app(client, register_user, email="reservations@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Reservas", "description": "", "template_type": "restaurant"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _future_iso(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def test_create_reservation_fails_for_draft_app(client, register_user):
    data = register_user(email="reservationsdraft@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Draft", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    response = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 2, "reservation_at": _future_iso()},
    )
    assert response.status_code == 404


def test_create_reservation_is_public_and_persists(client, register_user, db_session):
    app_id, _ = _published_app(client, register_user)

    response = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={
            "customer_name": "Cliente",
            "customer_phone": "11999999999",
            "party_size": 4,
            "reservation_at": _future_iso(),
            "notes": "Mesa perto da janela",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["party_size"] == 4
    assert body["table_number"] is None

    reservation = db_session.query(TableReservation).filter(TableReservation.app_id == app_id).first()
    assert reservation is not None
    assert reservation.customer_name == "Cliente"


def test_create_reservation_rejects_invalid_party_size(client, register_user):
    app_id, _ = _published_app(client, register_user, "reservationsparty@example.com")

    response = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 0, "reservation_at": _future_iso()},
    )
    assert response.status_code == 400


def test_create_reservation_rejects_past_datetime(client, register_user):
    app_id, _ = _published_app(client, register_user, "reservationspast@example.com")

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    response = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 2, "reservation_at": past},
    )
    assert response.status_code == 400


def test_create_reservation_respects_operating_hours(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "reservationshours@example.com")

    client.put(
        f"/api/apps/{app_id}/module-config/reserva_mesa",
        json={"settings": {"horario_funcionamento": "seg-dom:11:00-14:00"}},
        headers=owner_headers,
    )

    # Um domingo às 20h -- fora do horário configurado (11-14h todos os dias).
    next_sunday_evening = datetime.now(timezone.utc) + timedelta(days=7)
    next_sunday_evening = next_sunday_evening.replace(hour=20, minute=0, second=0, microsecond=0)

    response = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={
            "customer_name": "Cliente",
            "customer_phone": "11999999999",
            "party_size": 2,
            "reservation_at": next_sunday_evening.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "horário" in response.json()["detail"]


def test_owner_can_list_and_update_reservation(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "reservationsowner@example.com")

    created = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 3, "reservation_at": _future_iso()},
    )
    reservation_id = created.json()["id"]

    listed = client.get(f"/api/apps/{app_id}/modules/reserva_mesa/reservations", headers=owner_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/api/apps/{app_id}/reservations/{reservation_id}",
        json={"status": "confirmed", "table_number": "5"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "confirmed"
    assert updated.json()["table_number"] == "5"


def test_update_reservation_rejects_invalid_status(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "reservationsinvalid@example.com")

    created = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 2, "reservation_at": _future_iso()},
    )
    reservation_id = created.json()["id"]

    response = client.put(
        f"/api/apps/{app_id}/reservations/{reservation_id}",
        json={"status": "nao-existe"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_non_collaborator_cannot_see_or_update_reservations(client, register_user):
    app_id, _ = _published_app(client, register_user, "reservationsprivate-owner@example.com")
    stranger = register_user(email="reservationsprivate-stranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    created = client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 2, "reservation_at": _future_iso()},
    )
    reservation_id = created.json()["id"]

    listed = client.get(f"/api/apps/{app_id}/modules/reserva_mesa/reservations", headers=stranger_headers)
    assert listed.status_code == 404

    updated = client.put(
        f"/api/apps/{app_id}/reservations/{reservation_id}",
        json={"status": "confirmed"},
        headers=stranger_headers,
    )
    assert updated.status_code == 404


def test_my_reservations_requires_end_user_login(client, register_user):
    app_id, _ = _published_app(client, register_user, "reservationsenduser@example.com")

    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": "clientereserva@example.com", "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    end_user_headers = {"Authorization": f"Bearer {register_end_user.json()['access_token']}"}

    client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 2, "reservation_at": _future_iso()},
        headers=end_user_headers,
    )

    no_auth = client.get(f"/api/apps/{app_id}/my-reservations")
    assert no_auth.status_code == 401

    mine = client.get(f"/api/apps/{app_id}/my-reservations", headers=end_user_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["end_user_id"] is not None


def test_delete_app_cascades_reservations(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "reservationscascade@example.com")

    client.post(
        f"/api/apps/{app_id}/modules/reserva_mesa/reservations",
        json={"customer_name": "Cliente", "customer_phone": "11999999999", "party_size": 2, "reservation_at": _future_iso()},
    )

    deleted = client.delete(f"/api/apps/{app_id}", headers=owner_headers)
    assert deleted.status_code == 204

    remaining = db_session.query(TableReservation).filter(TableReservation.app_id == app_id).count()
    assert remaining == 0
