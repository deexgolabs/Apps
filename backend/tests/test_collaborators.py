from app.models import AppCollaborator, OwnerAuditLog


def _owner_with_app(client, register_user, email="collab-owner@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Equipe", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    return app_id, headers, data["user"]["id"]


def _other_user(client, register_user, email="collab-other@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return headers, data["user"]["id"]


def test_invite_requires_existing_account(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user)

    response = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "naoexiste@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_invite_requires_owner(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user)
    other_headers, _ = _other_user(client, register_user, "collab-notowner@example.com")

    response = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-notowner@example.com", "role": "editor"},
        headers=other_headers,
    )
    assert response.status_code == 404


def test_invite_rejects_duplicate_and_self(client, register_user):
    app_id, owner_headers, owner_id = _owner_with_app(client, register_user, "collab-dup-owner@example.com")
    other_headers, _ = _other_user(client, register_user, "collab-dup-other@example.com")

    first = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-dup-other@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-dup-other@example.com", "role": "viewer"},
        headers=owner_headers,
    )
    assert duplicate.status_code == 400

    self_invite = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-dup-owner@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert self_invite.status_code == 400


def test_editor_can_write_but_not_delete_or_manage_team(client, register_user):
    app_id, owner_headers, owner_id = _owner_with_app(client, register_user, "collab-editor-owner@example.com")
    editor_headers, editor_id = _other_user(client, register_user, "collab-editor@example.com")

    client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-editor@example.com", "role": "editor"},
        headers=owner_headers,
    )

    update = client.put(f"/api/apps/{app_id}", json={"name": "Renomeado pelo editor"}, headers=editor_headers)
    assert update.status_code == 200
    assert update.json()["name"] == "Renomeado pelo editor"
    assert update.json()["my_role"] == "editor"

    delete = client.delete(f"/api/apps/{app_id}", headers=editor_headers)
    assert delete.status_code == 404

    invite_attempt = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-editor-owner@example.com", "role": "viewer"},
        headers=editor_headers,
    )
    assert invite_attempt.status_code == 404


def test_viewer_can_read_but_not_write(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user, "collab-viewer-owner@example.com")
    viewer_headers, _ = _other_user(client, register_user, "collab-viewer@example.com")

    client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-viewer@example.com", "role": "viewer"},
        headers=owner_headers,
    )

    read = client.get(f"/api/apps/{app_id}", headers=viewer_headers)
    assert read.status_code == 200
    assert read.json()["my_role"] == "viewer"

    write = client.put(f"/api/apps/{app_id}", json={"name": "Tentativa"}, headers=viewer_headers)
    assert write.status_code == 404


def test_non_collaborator_gets_404(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user, "collab-private-owner@example.com")
    stranger_headers, _ = _other_user(client, register_user, "collab-stranger@example.com")

    read = client.get(f"/api/apps/{app_id}", headers=stranger_headers)
    assert read.status_code == 404

    write = client.put(f"/api/apps/{app_id}", json={"name": "x"}, headers=stranger_headers)
    assert write.status_code == 404


def test_list_apps_includes_collaborator_apps_with_role(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user, "collab-list-owner@example.com")
    editor_headers, _ = _other_user(client, register_user, "collab-list-editor@example.com")

    client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-list-editor@example.com", "role": "editor"},
        headers=owner_headers,
    )

    listed = client.get("/api/apps/", headers=editor_headers)
    assert listed.status_code == 200
    apps = listed.json()
    assert len(apps) == 1
    assert apps[0]["id"] == app_id
    assert apps[0]["my_role"] == "editor"


def test_collaborator_can_remove_self(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user, "collab-leave-owner@example.com")
    editor_headers, _ = _other_user(client, register_user, "collab-leave-editor@example.com")

    created = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-leave-editor@example.com", "role": "editor"},
        headers=owner_headers,
    )
    collaborator_id = created.json()["id"]

    leave = client.delete(f"/api/apps/{app_id}/collaborators/{collaborator_id}", headers=editor_headers)
    assert leave.status_code == 204

    read_after = client.get(f"/api/apps/{app_id}", headers=editor_headers)
    assert read_after.status_code == 404


def test_owner_can_remove_collaborator(client, register_user):
    app_id, owner_headers, _ = _owner_with_app(client, register_user, "collab-kick-owner@example.com")
    editor_headers, _ = _other_user(client, register_user, "collab-kick-editor@example.com")

    created = client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-kick-editor@example.com", "role": "editor"},
        headers=owner_headers,
    )
    collaborator_id = created.json()["id"]

    removed = client.delete(f"/api/apps/{app_id}/collaborators/{collaborator_id}", headers=owner_headers)
    assert removed.status_code == 204

    read_after = client.get(f"/api/apps/{app_id}", headers=editor_headers)
    assert read_after.status_code == 404


def test_editor_action_is_attributed_to_owner_in_audit_log(client, register_user, db_session):
    app_id, owner_headers, owner_id = _owner_with_app(client, register_user, "collab-audit-owner@example.com")
    editor_headers, editor_id = _other_user(client, register_user, "collab-audit-editor@example.com")

    client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-audit-editor@example.com", "role": "editor"},
        headers=owner_headers,
    )

    update = client.put(f"/api/apps/{app_id}", json={"name": "Editado pelo editor"}, headers=editor_headers)
    assert update.status_code == 200

    log = (
        db_session.query(OwnerAuditLog)
        .filter(OwnerAuditLog.app_id == app_id, OwnerAuditLog.action == "update_app")
        .order_by(OwnerAuditLog.created_at.desc())
        .first()
    )
    assert log is not None
    assert log.owner_id == owner_id
    assert log.owner_id != editor_id


def test_delete_app_cascades_collaborators(client, register_user, db_session):
    app_id, owner_headers, _ = _owner_with_app(client, register_user, "collab-cascade-owner@example.com")
    editor_headers, _ = _other_user(client, register_user, "collab-cascade-editor@example.com")

    client.post(
        f"/api/apps/{app_id}/collaborators",
        json={"email": "collab-cascade-editor@example.com", "role": "editor"},
        headers=owner_headers,
    )

    deleted = client.delete(f"/api/apps/{app_id}", headers=owner_headers)
    assert deleted.status_code == 204

    remaining = db_session.query(AppCollaborator).filter(AppCollaborator.app_id == app_id).count()
    assert remaining == 0
