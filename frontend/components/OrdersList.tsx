'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import type { Order } from '@/types'
import WhatsAppShareButton from '@/components/WhatsAppShareButton'
import { printComanda } from '@/lib/printComanda'

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pendente' },
  { value: 'confirmed', label: 'Confirmado' },
  { value: 'preparing', label: 'Preparando' },
  { value: 'completed', label: 'Concluído' },
  { value: 'cancelled', label: 'Cancelado' },
]

const FULFILLMENT_LABELS: Record<string, string> = {
  pickup: 'Retirada no local',
  delivery: 'Entrega',
}

function handlePrintOrder(appName: string, order: Order) {
  const fulfillment =
    order.fulfillment_type === 'dine_in'
      ? `Mesa ${order.table_number || ''}`
      : FULFILLMENT_LABELS[order.fulfillment_type || ''] || null

  const dataLines = Object.entries(order.data)
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n')

  try {
    printComanda({
      appName,
      title: `Pedido #${order.id}`,
      subtitle: [
        fulfillment,
        order.pickup_point ? `Retirada em: ${order.pickup_point}` : null,
        order.delivery_slot ? `Horário: ${order.delivery_slot}` : null,
        order.coupon_code ? `Cupom: ${order.coupon_code}` : null,
      ]
        .filter(Boolean)
        .join(' · ') || undefined,
      lines: order.items.map((oi) => ({ label: oi.name, qty: oi.quantity, unitPrice: oi.unit_price, total: oi.subtotal })),
      total: order.amount || 0,
      footer: dataLines || undefined,
    })
  } catch {
    toast.error('Habilite pop-ups pra imprimir a comanda')
  }
}

export default function OrdersList({ appId, appName, moduleName }: { appId: string; appName?: string; moduleName?: string }) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response = await api.get(`/api/apps/${appId}/orders`)
        const all: Order[] = response.data
        setOrders(moduleName ? all.filter((o) => o.module_name === moduleName) : all)
      } catch (error) {
        toast.error('Erro ao carregar pedidos')
      } finally {
        setLoading(false)
      }
    }
    fetchOrders()
  }, [appId, moduleName])

  const handleStatusChange = async (orderId: number, status: string) => {
    try {
      await api.put(`/api/apps/${appId}/orders/${orderId}`, { status })
      setOrders((prev) => prev.map((o) => (o.id === orderId ? { ...o, status } : o)))
    } catch (error) {
      toast.error('Erro ao atualizar status do pedido')
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  if (orders.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        Nenhum pedido recebido ainda. Teste o formulário na aba Preview.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">Pedidos recebidos ({orders.length})</p>
      {orders.map((order) => (
        <div key={order.id} className="border border-gray-200 rounded-lg p-3 text-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400">
              {new Date(order.created_at).toLocaleString('pt-BR')}
              {!moduleName && <span className="ml-2 text-gray-500 font-medium">{order.module_name}</span>}
            </p>
            <select
              value={order.status}
              onChange={(e) => handleStatusChange(order.id, e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          {order.items.length > 0 && (
            <table className="w-full text-xs">
              <tbody>
                {order.items.map((oi) => (
                  <tr key={oi.id} className="border-b border-gray-100 last:border-0">
                    <td className="py-1 text-gray-700">
                      {oi.quantity}x {oi.name}
                    </td>
                    <td className="py-1 text-right text-gray-500">R$ {oi.unit_price.toFixed(2)}</td>
                    <td className="py-1 text-right text-gray-700 font-medium">R$ {oi.subtotal.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {(order.fulfillment_type || order.coupon_code) && (
            <p className="text-xs text-gray-500">
              {order.fulfillment_type === 'pickup'
                ? '🏠 Retirada no local'
                : order.fulfillment_type === 'delivery'
                  ? '🚚 Entrega'
                  : order.fulfillment_type === 'dine_in'
                    ? `🍽️ Mesa ${order.table_number || ''}`
                    : null}
              {order.pickup_point && <span className="ml-2">📍 {order.pickup_point}</span>}
              {order.delivery_slot && <span className="ml-2">🕐 {order.delivery_slot}</span>}
              {order.coupon_code && <span className="ml-2">🏷️ Cupom: {order.coupon_code}</span>}
            </p>
          )}
          {order.subtotal != null && (order.delivery_fee || order.discount_amount) ? (
            <div className="text-xs text-gray-500 space-y-0.5">
              <p>Subtotal: R$ {order.subtotal.toFixed(2)}</p>
              {!!order.delivery_fee && <p>Frete: R$ {order.delivery_fee.toFixed(2)}</p>}
              {!!order.discount_amount && <p>Desconto: -R$ {order.discount_amount.toFixed(2)}</p>}
            </div>
          ) : null}
          {order.amount != null && (
            <p className="text-gray-700 font-medium">Total: R$ {order.amount.toFixed(2)}</p>
          )}
          {Object.entries(order.data).map(([key, value]) => (
            <p key={key} className="text-gray-700">
              <span className="font-medium">{key}:</span> {String(value)}
            </p>
          ))}
          <div className="pt-1 border-t border-gray-100 flex items-center gap-2">
            <WhatsAppShareButton order={order} />
            <button
              type="button"
              onClick={() => handlePrintOrder(appName || 'Loja', order)}
              className="text-xs text-gray-600 border border-gray-300 rounded px-2 py-1 hover:bg-gray-50"
            >
              🖨️ Imprimir comanda
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
