'use client'

import type { Order } from '@/types'

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  confirmed: 'Confirmado',
  preparing: 'Preparando',
  completed: 'Concluído',
  cancelled: 'Cancelado',
}

function buildOrderText(order: Order): string {
  const lines = [`Pedido #${order.id} (${STATUS_LABELS[order.status] || order.status})`]

  if (order.table_number) lines.push(`Mesa: ${order.table_number}`)

  if (order.items.length > 0) {
    lines.push('', 'Itens:')
    order.items.forEach((oi) => lines.push(`${oi.quantity}x ${oi.name} — R$ ${oi.subtotal.toFixed(2)}`))
  }

  Object.entries(order.data || {}).forEach(([key, value]) => {
    if (value) lines.push(`${key}: ${value}`)
  })

  if (order.amount != null) lines.push('', `Total: R$ ${order.amount.toFixed(2)}`)

  return lines.join('\n')
}

/** 100% client-side — monta o texto do pedido e abre o WhatsApp sem um número
 * fixo, deixando o lojista escolher pra quem enviar (cozinha, entregador...). */
export default function WhatsAppShareButton({ order }: { order: Order }) {
  const handleShare = () => {
    const text = encodeURIComponent(buildOrderText(order))
    window.open(`https://wa.me/?text=${text}`, '_blank', 'noopener,noreferrer')
  }

  return (
    <button
      type="button"
      onClick={handleShare}
      className="text-green-600 hover:text-green-700 font-medium"
      title="Compartilhar pedido no WhatsApp"
    >
      📱 WhatsApp
    </button>
  )
}
