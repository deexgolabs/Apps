"""Funções de checkout reutilizadas tanto pelos módulos de pagamento dentro dos
apps dos clientes (app/routes/payments.py) quanto pela cobrança da própria
plataforma (app/routes/billing.py)."""
import httpx
from fastapi import HTTPException, status


async def checkout_mercado_pago(valor: float, titulo: str, access_token: str, external_reference: str | None = None) -> dict:
    payload = {"items": [{"title": titulo, "quantity": 1, "unit_price": valor, "currency_id": "BRL"}]}
    if external_reference:
        payload["external_reference"] = external_reference

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.mercadopago.com/checkout/preferences",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro do Mercado Pago: {response.text}"
        )

    return {"checkout_url": response.json().get("init_point")}


async def verify_mercado_pago(external_reference: str, access_token: str) -> bool:
    """Consulta se existe algum pagamento aprovado para o external_reference (id do
    nosso Order) — é assim que se liga um Order nosso a um pagamento real da gateway,
    já que a preferência de checkout não devolve o payment_id (só existe depois que
    o cliente paga)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.mercadopago.com/v1/payments/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"external_reference": external_reference},
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro do Mercado Pago: {response.text}"
        )

    results = response.json().get("results", [])
    return any(r.get("status") == "approved" for r in results)


async def checkout_paypal(valor, titulo: str, client_id: str, client_secret: str) -> dict:
    base_url = "https://api-m.sandbox.paypal.com"

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        if token_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro de autenticação do PayPal: {token_response.text}"
            )

        access_token = token_response.json().get("access_token")
        order_response = await client.post(
            f"{base_url}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{"description": titulo, "amount": {"currency_code": "BRL", "value": str(valor)}}],
            },
        )

    if order_response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro do PayPal: {order_response.text}"
        )

    data = order_response.json()
    approve_link = next((link["href"] for link in data.get("links", []) if link.get("rel") == "approve"), None)
    return {"checkout_url": approve_link, "gateway_order_id": data.get("id")}


async def verify_paypal(paypal_order_id: str, client_id: str, client_secret: str) -> bool:
    """Consulta o status do pedido no PayPal e, se o cliente já aprovou mas ainda não
    foi capturado, captura o pagamento — só depois da captura o dinheiro é considerado
    liquidado do lado do PayPal."""
    base_url = "https://api-m.sandbox.paypal.com"

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        if token_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro de autenticação do PayPal: {token_response.text}"
            )
        access_token = token_response.json().get("access_token")

        order_response = await client.get(
            f"{base_url}/v2/checkout/orders/{paypal_order_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if order_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro do PayPal: {order_response.text}"
            )

        order_status = order_response.json().get("status")
        if order_status == "COMPLETED":
            return True
        if order_status != "APPROVED":
            return False

        capture_response = await client.post(
            f"{base_url}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if capture_response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao capturar pagamento no PayPal: {capture_response.text}"
        )

    return capture_response.json().get("status") == "COMPLETED"


async def checkout_pagseguro(valor: float, titulo: str, token: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://sandbox.api.pagseguro.com/orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"items": [{"name": titulo, "quantity": 1, "unit_amount": int(valor * 100)}]},
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro do PagSeguro: {response.text}"
        )

    data = response.json()
    checkout_url = next((link["href"] for link in data.get("links", []) if link.get("rel") == "PAY"), None)
    return {"checkout_url": checkout_url, "gateway_order_id": data.get("id")}


async def verify_pagseguro(pagseguro_order_id: str, token: str) -> bool:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"https://sandbox.api.pagseguro.com/orders/{pagseguro_order_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro do PagSeguro: {response.text}"
        )

    charges = response.json().get("charges", [])
    return any(c.get("status") == "PAID" for c in charges)
