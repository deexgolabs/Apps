'use client'

import { useState } from 'react'
import { publicApi } from '@/lib/api'
import { PAGAMENTO_ENTREGA_CUSTOMER_FIELDS } from '@/lib/moduleFields'
import { endUserAuthHeader } from '@/lib/endUserAuth'
import { useCart } from '@/context/CartContext'
import { showApiError } from '@/lib/apiError'
import { computeFrete } from '@/lib/frete'

export default function CheckoutForm({
  appId,
  onDone,
  freteRegras,
  allowPickup = true,
}: {
  appId: string
  onDone: () => void
  freteRegras?: string
  allowPickup?: boolean
}) {
  const cart = useCart()
  const [values, setValues] = useState<Record<string, string>>({})
  const [cep, setCep] = useState('')
  const [fulfillment, setFulfillment] = useState<'delivery' | 'pickup'>('delivery')
  const [couponInput, setCouponInput] = useState('')
  const [couponDiscount, setCouponDiscount] = useState<number | null>(null)
  const [couponError, setCouponError] = useState<string | null>(null)
  const [validatingCoupon, setValidatingCoupon] = useState(false)
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  if (!cart.cartModuleName) return null

  const deliveryFee = fulfillment === 'delivery' ? computeFrete(freteRegras || '', cep) : 0
  const total = cart.subtotal + deliveryFee - (couponDiscount || 0)

  const handleValidateCoupon = async () => {
    if (!couponInput.trim()) {
      setCouponDiscount(null)
      setCouponError(null)
      return
    }
    setValidatingCoupon(true)
    try {
      const res = await publicApi.post(`/api/apps/${appId}/public/coupons/validate`, {
        code: couponInput,
        subtotal: cart.subtotal,
      })
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
      await publicApi.post(
        `/api/apps/${appId}/modules/${cart.cartModuleName}/cart-checkout`,
        {
          items: cart.items.map((i) => ({ item_id: i.item_id, variation_id: i.variation_id, quantity: i.quantity })),
          customer: { ...values, ...(fulfillment === 'delivery' ? { cep } : {}) },
          coupon_code: couponInput.trim() || undefined,
          fulfillment_type: fulfillment,
          cep: fulfillment === 'delivery' ? cep : undefined,
        },
        { headers: endUserAuthHeader(appId) }
      )
      setSent(true)
      cart.clear()
    } catch (error) {
      showApiError(error, 'Erro ao fechar pedido')
    } finally {
      setSending(false)
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
        {sending ? 'Enviando...' : `Confirmar pedido — R$ ${total.toFixed(2)}`}
      </button>
    </div>
  )
}
