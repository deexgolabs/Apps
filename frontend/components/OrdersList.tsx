'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface Order {
  id: number
  module_name: string
  data: Record<string, any>
  amount: number | null
  payment_method: string | null
  status: string
  created_at: string
}

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pendente' },
  { value: 'confirmed', label: 'Confirmado' },
  { value: 'preparing', label: 'Preparando' },
  { value: 'completed', label: 'Concluído' },
  { value: 'cancelled', label: 'Cancelado' },
]

export default function OrdersList({ appId, moduleName }: { appId: string; moduleName?: string }) {
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
          {order.amount != null && (
            <p className="text-gray-700 font-medium">R$ {order.amount.toFixed(2)}</p>
          )}
          {Object.entries(order.data).map(([key, value]) => (
            <p key={key} className="text-gray-700">
              <span className="font-medium">{key}:</span> {String(value)}
            </p>
          ))}
        </div>
      ))}
    </div>
  )
}
