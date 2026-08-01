'use client'

import { useState } from 'react'
import { useCart } from '@/context/CartContext'
import CheckoutForm from '@/components/CheckoutForm'

export default function CartDrawer({
  appId,
  open,
  onClose,
  freteRegras,
  availableGateways,
  pontosRetirada,
  janelaHorarios,
}: {
  appId: string
  open: boolean
  onClose: () => void
  freteRegras?: string
  availableGateways?: string[]
  pontosRetirada?: string
  janelaHorarios?: string
}) {
  const cart = useCart()
  const [checkingOut, setCheckingOut] = useState(false)

  if (!open) return null

  return (
    <div className="absolute inset-0 z-30 bg-white/95 flex flex-col">
      <div className="h-10 flex items-center justify-between px-3 bg-gray-800">
        <span className="text-white text-sm font-semibold">
          {checkingOut ? 'Finalizar pedido' : 'Seu carrinho'}
        </span>
        <button
          type="button"
          onClick={() => {
            setCheckingOut(false)
            onClose()
          }}
          className="text-white text-lg leading-none"
          aria-label="Fechar carrinho"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {checkingOut ? (
          <CheckoutForm
            appId={appId}
            freteRegras={freteRegras}
            availableGateways={availableGateways}
            pontosRetirada={pontosRetirada}
            janelaHorarios={janelaHorarios}
            onDone={() => {
              setCheckingOut(false)
              onClose()
            }}
          />
        ) : cart.items.length === 0 ? (
          <p className="text-sm text-gray-400 italic text-center mt-8">Seu carrinho está vazio</p>
        ) : (
          <div className="space-y-3">
            {cart.items.map((item) => (
              <div key={`${item.item_id}-${item.variation_ids.join(',')}`} className="flex items-center gap-2 border-b border-gray-100 pb-2">
                {item.image_url && (
                  <img src={item.image_url} alt="" className="w-10 h-10 object-cover rounded flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                  <p className="text-xs text-gray-500">R$ {item.unit_price.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => cart.setQuantity(item.item_id, item.quantity - 1, item.variation_ids)}
                    className="w-6 h-6 rounded bg-gray-100 text-gray-700 text-sm"
                  >
                    −
                  </button>
                  <span className="text-sm w-5 text-center">{item.quantity}</span>
                  <button
                    type="button"
                    onClick={() => cart.setQuantity(item.item_id, item.quantity + 1, item.variation_ids)}
                    disabled={item.stock !== null && item.quantity >= item.stock}
                    className="w-6 h-6 rounded bg-gray-100 text-gray-700 text-sm disabled:opacity-40"
                  >
                    +
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {!checkingOut && cart.items.length > 0 && (
        <div className="border-t border-gray-200 p-3">
          <div className="flex justify-between text-sm font-medium mb-2">
            <span>Subtotal</span>
            <span>R$ {cart.subtotal.toFixed(2)}</span>
          </div>
          <button
            type="button"
            onClick={() => setCheckingOut(true)}
            className="w-full bg-indigo-600 text-white text-sm font-medium rounded py-2"
          >
            Finalizar pedido
          </button>
        </div>
      )}
    </div>
  )
}
