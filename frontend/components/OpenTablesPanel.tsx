'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import type { Order } from '@/types'
import { printComanda } from '@/lib/printComanda'

function handlePrintTable(appName: string, tableNumber: string, tableOrders: Order[]) {
  const lines = tableOrders.flatMap((o) =>
    o.items.map((oi) => ({ label: oi.name, qty: oi.quantity, unitPrice: oi.unit_price, total: oi.subtotal }))
  )
  const total = tableOrders.reduce((sum, o) => sum + (o.amount || 0), 0)

  try {
    printComanda({
      appName,
      title: `Mesa ${tableNumber}`,
      subtitle: `${tableOrders.length} pedido(s)`,
      lines,
      total,
    })
  } catch {
    toast.error('Habilite pop-ups pra imprimir a comanda')
  }
}

export default function OpenTablesPanel({ appId, appName }: { appId: string; appName?: string }) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [closingTable, setClosingTable] = useState<string | null>(null)

  const fetchOrders = () => {
    api
      .get(`/api/apps/${appId}/orders`)
      .then((res) => setOrders(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchOrders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const openOrders = orders.filter(
    (o) => o.fulfillment_type === 'dine_in' && o.table_number && !['completed', 'cancelled'].includes(o.status)
  )

  const tables = Array.from(new Set(openOrders.map((o) => o.table_number as string))).sort()

  const handleCloseTable = async (tableNumber: string) => {
    if (!window.confirm(`Fechar a comanda da mesa ${tableNumber}? Todos os pedidos em aberto serão marcados como concluídos.`)) return
    setClosingTable(tableNumber)
    try {
      await api.put(`/api/apps/${appId}/orders/close-table`, { table_number: tableNumber })
      toast.success(`Comanda da mesa ${tableNumber} fechada!`)
      fetchOrders()
    } catch (error) {
      toast.error('Erro ao fechar comanda')
    } finally {
      setClosingTable(null)
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Carregando mesas...</p>

  if (tables.length === 0) {
    return <p className="text-sm text-gray-400 italic">Nenhuma mesa com pedido em aberto no momento.</p>
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">Mesas abertas ({tables.length})</p>
      {tables.map((tableNumber) => {
        const tableOrders = openOrders.filter((o) => o.table_number === tableNumber)
        const total = tableOrders.reduce((sum, o) => sum + (o.amount || 0), 0)
        return (
          <div key={tableNumber} className="border border-gray-200 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900">Mesa {tableNumber}</p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handlePrintTable(appName || 'Loja', tableNumber, tableOrders)}
                  className="text-xs text-gray-600 border border-gray-300 rounded px-2 py-1 hover:bg-gray-50"
                >
                  🖨️ Imprimir
                </button>
                <button
                  type="button"
                  onClick={() => handleCloseTable(tableNumber)}
                  disabled={closingTable === tableNumber}
                  className="text-xs bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700 disabled:opacity-50"
                >
                  {closingTable === tableNumber ? 'Fechando...' : 'Fechar comanda'}
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-600 space-y-1">
              {tableOrders.map((o) => (
                <p key={o.id}>
                  Pedido #{o.id} — {o.items.map((oi) => `${oi.quantity}x ${oi.name}`).join(', ')} — R$ {(o.amount || 0).toFixed(2)}
                </p>
              ))}
            </div>
            <p className="text-sm font-semibold text-gray-900 pt-1 border-t border-gray-100">
              Total: R$ {total.toFixed(2)}
            </p>
          </div>
        )
      })}
    </div>
  )
}
