'use client'

import { useState } from 'react'
import { publicApi } from '@/lib/api'
import { PAGAMENTO_ENTREGA_CUSTOMER_FIELDS } from '@/lib/moduleFields'
import { endUserAuthHeader, endUserSessionKey } from '@/lib/endUserAuth'
import { useCart } from '@/context/CartContext'
import { showApiError } from '@/lib/apiError'
import { computeFrete } from '@/lib/frete'
import { generateDeliverySlots, parsePickupPoints } from '@/lib/deliverySlots'
import toast from 'react-hot-toast'

const GATEWAY_LABELS: Record<string, string> = {
  mercado_pago: 'Mercado Pago',
  paypal: 'PayPal',
  pagseguro: 'PagSeguro',
}

export default function CheckoutForm({
  appId,
  onDone,
  freteRegras,
  allowPickup = true,
  availableGateways = [],
  pontosRetirada,
  janelaHorarios,
}: {
  appId: string
  onDone: () => void
  freteRegras?: string
  allowPickup?: boolean
  availableGateways?: string[]
  pontosRetirada?: string
  janelaHorarios?: string
}) {
  const cart = useCart()
  const [values, setValues] = useState<Record<string, string>>(() => {
    // Pré-preenche com os dados salvos no perfil do cliente (se ele estiver
    // logado via login_cadastro) — economiza redigitar nome/telefone/endereço
    // a cada pedido novo.
    try {
      const saved = localStorage.getItem(endUserSessionKey(appId))
      if (!saved) return {}
      const { user } = JSON.parse(saved)
      const prefilled: Record<string, string> = {}
      if (user?.full_name) prefilled.nome = user.full_name
      if (user?.phone) prefilled.telefone = user.phone
      if (user?.address) prefilled.endereco = user.address
      return prefilled
    } catch {
      return {}
    }
  })
  const [cep, setCep] = useState('')
  const [fulfillment, setFulfillment] = useState<'delivery' | 'pickup' | 'dine_in'>('delivery')
  const [tableNumber, setTableNumber] = useState('')
  const [pickupPoint, setPickupPoint] = useState('')
  const [deliverySlot, setDeliverySlot] = useState('')
  const [couponInput, setCouponInput] = useState('')
  const [couponDiscount, setCouponDiscount] = useState<number | null>(null)
  const [couponError, setCouponError] = useState<string | null>(null)
  const [validatingCoupon, setValidatingCoupon] = useState(false)
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [paymentMethod, setPaymentMethod] = useState<'entrega' | string>('entrega')
  const [gatewayOrderId, setGatewayOrderId] = useState<number | null>(null)
  const [gatewayStatus, setGatewayStatus] = useState<string | null>(null)
  const [confirmingPayment, setConfirmingPayment] = useState(false)

  // cart.clear() zera o cartModuleName (derivado de items[0]) no mesmo
  // instante em que confirmamos o pedido — sem a exceção abaixo, a tela de
  // "Pedido confirmado!"/aguardando pagamento nunca chegaria a aparecer.
  if (!cart.cartModuleName && !sent && !gatewayOrderId) return null

  // comanda/mesa só faz sentido pra cardápio de restaurante, não pro catálogo
  // de loja/retail — os dois módulos são os únicos com carrinho habilitado.
  const allowDineIn = cart.cartModuleName === 'cardapio'
  const deliveryFee = fulfillment === 'delivery' ? computeFrete(freteRegras || '', cep) : 0
  const total = cart.subtotal + deliveryFee - (couponDiscount || 0)
  const pickupPoints = parsePickupPoints(pontosRetirada || '')
  const deliverySlots = fulfillment !== 'dine_in' ? generateDeliverySlots(janelaHorarios || '') : []

  const handleValidateCoupon = async () => {
    if (!couponInput.trim()) {
      setCouponDiscount(null)
      setCouponError(null)
      return
    }
    setValidatingCoupon(true)
    try {
      const res = await publicApi.post(
        `/api/apps/${appId}/public/coupons/validate`,
        { code: couponInput, subtotal: cart.subtotal },
        { headers: endUserAuthHeader(appId) }
      )
      if (res.data.valid) {
        setCouponDiscount(res.data.discount_amount)
        setCouponError(null)
      } else {
        setCouponDiscount(null)
        setCouponError(res.data.reason || 'Cupom inválido')
      }
    } catch {
      setCouponDiscount(null)
      setCouponError('Erro ao validar cupom')
    } finally {
      setValidatingCoupon(false)
    }
  }

  const handleSubmit = async () => {
    setSending(true)
    try {
      const response = await publicApi.post(
        `/api/apps/${appId}/modules/${cart.cartModuleName}/cart-checkout`,
        {
          items: cart.items.map((i) => ({ item_id: i.item_id, variation_ids: i.variation_ids, quantity: i.quantity })),
          customer: { ...values, ...(fulfillment === 'delivery' ? { cep } : {}) },
          coupon_code: couponInput.trim() || undefined,
          fulfillment_type: fulfillment,
          cep: fulfillment === 'delivery' ? cep : undefined,
          table_number: fulfillment === 'dine_in' ? tableNumber.trim() || undefined : undefined,
          pickup_point: fulfillment === 'pickup' ? pickupPoint || undefined : undefined,
          delivery_slot: fulfillment !== 'dine_in' ? deliverySlot || undefined : undefined,
          gateway: paymentMethod !== 'entrega' ? paymentMethod : undefined,
        },
        { headers: endUserAuthHeader(appId) }
      )

      if (paymentMethod !== 'entrega') {
        const url = response.data.checkout_url
        if (url) {
          window.open(url, '_blank', 'noopener,noreferrer')
          setGatewayOrderId(response.data.id)
          setGatewayStatus('pending')
          cart.clear()
        } else {
          toast.error('A gateway não retornou um link de pagamento')
        }
      } else {
        setSent(true)
        cart.clear()
      }
    } catch (error) {
      showApiError(error, 'Erro ao fechar pedido')
    } finally {
      setSending(false)
    }
  }

  const handleConfirmGatewayPayment = async () => {
    if (!gatewayOrderId) return
    setConfirmingPayment(true)
    try {
      const response = await publicApi.post(`/api/apps/${appId}/orders/${gatewayOrderId}/confirm-payment`)
      setGatewayStatus(response.data.status)
      if (response.data.status === 'confirmed') {
        toast.success('Pagamento confirmado!')
      } else {
        toast.error('Ainda não identificamos o pagamento. Tente novamente após concluir no checkout.')
      }
    } catch (error) {
      showApiError(error, 'Erro ao confirmar pagamento')
    } finally {
      setConfirmingPayment(false)
    }
  }

  if (sent) {
    return (
      <div className="text-center py-6">
        <p className="text-green-600 font-medium">Pedido confirmado!</p>
        <button type="button" onClick={onDone} className="mt-3 text-sm text-indigo-600 underline">
          Voltar
        </button>
      </div>
    )
  }

  if (gatewayOrderId) {
    return (
      <div className="text-center py-6 space-y-3">
        {gatewayStatus === 'confirmed' ? (
          <p className="text-green-600 font-medium">Pagamento confirmado!</p>
        ) : (
          <>
            <p className="text-sm text-gray-700">
              Complete o pagamento na aba que abrimos e depois confirme aqui.
            </p>
            <button
              type="button"
              onClick={handleConfirmGatewayPayment}
              disabled={confirmingPayment}
              className="bg-indigo-600 text-white text-sm font-medium rounded py-2 px-4 disabled:opacity-50"
            >
              {confirmingPayment ? 'Verificando...' : 'Já paguei'}
            </button>
          </>
        )}
        <div>
          <button type="button" onClick={onDone} className="text-sm text-indigo-600 underline">
            Voltar
          </button>
        </div>
      </div>
    )
  }

  const fields = PAGAMENTO_ENTREGA_CUSTOMER_FIELDS.filter(
    (f) => fulfillment === 'delivery' || f.key !== 'endereco'
  )

  return (
    <div className="space-y-3">
      {allowPickup && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setFulfillment('delivery')}
            className={`flex-1 text-xs font-medium py-1.5 rounded border ${
              fulfillment === 'delivery' ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'
            }`}
          >
            Entrega
          </button>
          <button
            type="button"
            onClick={() => setFulfillment('pickup')}
            className={`flex-1 text-xs font-medium py-1.5 rounded border ${
              fulfillment === 'pickup' ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'
            }`}
          >
            Retirada
          </button>
          {allowDineIn && (
            <button
              type="button"
              onClick={() => setFulfillment('dine_in')}
              className={`flex-1 text-xs font-medium py-1.5 rounded border ${
                fulfillment === 'dine_in' ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'
              }`}
            >
              Na mesa
            </button>
          )}
        </div>
      )}

      {fulfillment === 'dine_in' && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Número da mesa</label>
          <input
            type="text"
            value={tableNumber}
            onChange={(e) => setTableNumber(e.target.value)}
            placeholder="Ex: 5"
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          />
        </div>
      )}

      {fulfillment === 'pickup' && pickupPoints.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Ponto de retirada</label>
          <select
            value={pickupPoint}
            onChange={(e) => setPickupPoint(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">Selecione...</option>
            {pickupPoints.map((p) => (
              <option key={p.name} value={p.address ? `${p.name}: ${p.address}` : p.name}>
                {p.name}
                {p.address ? ` — ${p.address}` : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {deliverySlots.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Horário de {fulfillment === 'pickup' ? 'retirada' : 'entrega'}
          </label>
          <select
            value={deliverySlot}
            onChange={(e) => setDeliverySlot(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">Selecione...</option>
            {deliverySlots.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {fields.map((field) => (
        <div key={field.key}>
          <label className="block text-xs font-medium text-gray-600 mb-1">{field.label}</label>
          {field.type === 'textarea' ? (
            <textarea
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              rows={2}
              value={values[field.key] || ''}
              onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
            />
          ) : (
            <input
              type="text"
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              value={values[field.key] || ''}
              onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
            />
          )}
        </div>
      ))}

      {fulfillment === 'delivery' && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">CEP</label>
          <input
            type="text"
            value={cep}
            onChange={(e) => setCep(e.target.value)}
            placeholder="00000-000"
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          />
        </div>
      )}

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Cupom de desconto (opcional)</label>
        <input
          type="text"
          value={couponInput}
          onChange={(e) => {
            setCouponInput(e.target.value)
            setCouponDiscount(null)
            setCouponError(null)
          }}
          onBlur={handleValidateCoupon}
          placeholder="CODIGO"
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
        />
        {validatingCoupon && <p className="text-[11px] text-gray-400 mt-0.5">Validando...</p>}
        {couponDiscount != null && (
          <p className="text-[11px] text-green-600 mt-0.5">Desconto de R$ {couponDiscount.toFixed(2)} aplicado</p>
        )}
        {couponError && <p className="text-[11px] text-red-600 mt-0.5">{couponError}</p>}
      </div>

      {availableGateways.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Forma de pagamento</label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setPaymentMethod('entrega')}
              className={`text-xs font-medium py-1.5 px-2 rounded border ${
                paymentMethod === 'entrega' ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'
              }`}
            >
              Na entrega
            </button>
            {availableGateways.map((gw) => (
              <button
                key={gw}
                type="button"
                onClick={() => setPaymentMethod(gw)}
                className={`text-xs font-medium py-1.5 px-2 rounded border ${
                  paymentMethod === gw ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'
                }`}
              >
                {GATEWAY_LABELS[gw] || gw}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-gray-200 pt-2 space-y-0.5 text-xs">
        <div className="flex justify-between text-gray-600">
          <span>Subtotal</span>
          <span>R$ {cart.subtotal.toFixed(2)}</span>
        </div>
        {deliveryFee > 0 && (
          <div className="flex justify-between text-gray-600">
            <span>Frete</span>
            <span>R$ {deliveryFee.toFixed(2)}</span>
          </div>
        )}
        {!!couponDiscount && (
          <div className="flex justify-between text-green-600">
            <span>Desconto</span>
            <span>- R$ {couponDiscount.toFixed(2)}</span>
          </div>
        )}
        <div className="flex justify-between font-semibold text-gray-900">
          <span>Total</span>
          <span>R$ {total.toFixed(2)}</span>
        </div>
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={sending}
        className="w-full bg-indigo-600 text-white text-sm font-medium rounded py-2 disabled:opacity-50"
      >
        {sending
          ? 'Enviando...'
          : paymentMethod === 'entrega'
            ? `Confirmar pedido — R$ ${total.toFixed(2)}`
            : `Pagar com ${GATEWAY_LABELS[paymentMethod] || paymentMethod} — R$ ${total.toFixed(2)}`}
      </button>
    </div>
  )
}
