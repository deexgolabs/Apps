from app.models import (
    App,
    AppUser,
    AppVersion,
    Coupon,
    FormSubmission,
    ItemReview,
    ItemVariation,
    LoyaltyAccount,
    ModuleCategory,
    ModuleItem,
    Order,
    OrderItem,
    PushSubscription,
    WishlistItem,
)


def _published_app(client, register_user, email="delapp@example.com", plan="pro"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Exclusao", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers, data["user"]["id"]


def test_delete_app_removes_all_child_rows(client, register_user, db_session):
    """Regressão: deletar um app com categorias, itens, variações, avaliações,
    pedidos, cupons, usuários finais e assinaturas push dava 500 (violação de FK)
    porque nem routes/apps.py nem routes/admin.py limpavam todas as tabelas
    filhas antes de excluir o app."""
    from app.models import User

    app_id, headers, user_id = _published_app(client, register_user)
    user = db_session.query(User).filter(User.id == user_id).first()
    user.plan = "pro"
    db_session.commit()

    category = client.post(
        f"/api/apps/{app_id}/modules/catalogo/categories",
        json={"name": "Categoria"},
        headers=headers,
    )
    assert category.status_code == 201, category.text

    item = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items",
        json={"name": "Item", "price": 10.0, "category_id": category.json()["id"]},
        headers=headers,
    )
    assert item.status_code == 201, item.text
    item_id = item.json()["id"]

    variation = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/variations",
        json={"name": "Grande", "price": 15.0, "stock": 5},
        headers=headers,
    )
    assert variation.status_code == 201, variation.text

    end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": "cliente_delapp@example.com", "password": "senha12345", "full_name": "Cliente"},
    )
    assert end_user.status_code == 201, end_user.text
    end_user_headers = {"Authorization": f"Bearer {end_user.json()['access_token']}"}

    review = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/reviews",
        json={"rating": 5, "comment": "Ótimo"},
        headers=end_user_headers,
    )
    assert review.status_code == 200, review.text

    checkout = client.post(
        f"/api/apps/{app_id}/modules/catalogo/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    assert checkout.status_code == 201, checkout.text

    coupon = client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "PROMO", "discount_type": "percent", "discount_value": 10},
        headers=headers,
    )
    assert coupon.status_code == 201, coupon.text

    wishlist = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items/{item_id}/wishlist",
        headers=end_user_headers,
    )
    assert wishlist.status_code == 200, wishlist.text

    config = client.put(
        f"/api/apps/{app_id}/module-config/cartao_fidelidade",
        json={"settings": {"pontos_por_real": 1}},
        headers=headers,
    )
    assert config.status_code == 200, config.text
    order_id = checkout.json()["id"]
    completed = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert completed.status_code == 200, completed.text

    submission = client.post(
        f"/api/apps/{app_id}/modules/fale_conosco/submissions",
        json={"data": {"nome": "Visitante"}},
    )
    assert submission.status_code == 201, submission.text

    subscription = client.post(
        f"/api/apps/{app_id}/public/push/subscribe",
        json={
            "endpoint": "https://fcm.example.com/send/delapp",
            "keys": {"p256dh": "fake-p256dh", "auth": "fake-auth"},
        },
    )
    assert subscription.status_code == 201, subscription.text

    rename = client.put(f"/api/apps/{app_id}", json={"name": "App Exclusao Renomeado"}, headers=headers)
    assert rename.status_code == 200, rename.text
    assert db_session.query(AppVersion).filter(AppVersion.app_id == app_id).count() == 1

    deleted = client.delete(f"/api/apps/{app_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    assert db_session.query(App).filter(App.id == app_id).first() is None
    assert db_session.query(ModuleCategory).filter(ModuleCategory.app_id == app_id).count() == 0
    assert db_session.query(ModuleItem).filter(ModuleItem.app_id == app_id).count() == 0
    assert db_session.query(ItemVariation).filter(ItemVariation.item_id == item_id).count() == 0
    assert db_session.query(ItemReview).filter(ItemReview.item_id == item_id).count() == 0
    assert db_session.query(Order).filter(Order.app_id == app_id).count() == 0
    assert db_session.query(OrderItem).filter(OrderItem.module_item_id == item_id).count() == 0
    assert db_session.query(Coupon).filter(Coupon.app_id == app_id).count() == 0
    assert db_session.query(FormSubmission).filter(FormSubmission.app_id == app_id).count() == 0
    assert db_session.query(PushSubscription).filter(PushSubscription.app_id == app_id).count() == 0
    assert db_session.query(AppUser).filter(AppUser.app_id == app_id).count() == 0
    assert db_session.query(WishlistItem).filter(WishlistItem.app_id == app_id).count() == 0
    assert db_session.query(LoyaltyAccount).filter(LoyaltyAccount.app_id == app_id).count() == 0
    assert db_session.query(AppVersion).filter(AppVersion.app_id == app_id).count() == 0
