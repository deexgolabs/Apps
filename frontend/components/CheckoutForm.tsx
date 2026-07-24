'use client'

import { useState } from 'react'
import { publicApi } from '@/lib/api'
import { PAGAMENTO_ENTREGA_CUSTOMER_FIELDS } from '@/lib/moduleFields'
import { endUserAuthHeader } from '@/lib/endUserAuth'
import { useCart } from '@/context/CartContext'
import { showApiError } from '@/lib/apiError'

export default function CheckoutForm({
  appId,
  onDone,
}: {
  appId: string
  onDone: () => void
}) {
  const cart = useCart()
  const [values, setValues] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  if (!cart.cartModuleName) return null

  const handleSubmit = async () => {
    setSending(true)
    try {
      await publicApi.post(
        `/api/apps/${appId}/modules/${cart.cartModuleName}/cart-checkout`,
        {
          items: cart.items.map((i) => ({ item_id: i.item_id, quantity: i.quantity })),
          customer: values,
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

  return (
    <div className="space-y-3">
      {PAGAMENTO_ENTREGA_CUSTOMER_FIELDS.map((field) => (
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
      <button
        type="button"
        onClick={handleSubmit}
        disabled={sending}
        className="w-full bg-indigo-600 text-white text-sm font-medium rounded py-2 disabled:opacity-50"
      >
        {sending ? 'Enviando...' : `Confirmar pedido — R$ ${cart.subtotal.toFixed(2)}`}
      </button>
    </div>
  )
}
