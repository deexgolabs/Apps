'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import type { Reservation } from '@/types'

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pendente' },
  { value: 'confirmed', label: 'Confirmada' },
  { value: 'completed', label: 'Concluída' },
  { value: 'cancelled', label: 'Cancelada' },
]

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-700',
}

export default function ReservationsManager({ appId, moduleName }: { appId: string; moduleName: string }) {
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [loading, setLoading] = useState(true)
  const [tableDrafts, setTableDrafts] = useState<Record<number, string>>({})

  const fetchReservations = async () => {
    try {
      const res = await api.get<Reservation[]>(`/api/apps/${appId}/modules/${moduleName}/reservations`)
      setReservations(res.data)
    } catch {
      toast.error('Erro ao carregar reservas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReservations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId, moduleName])

  const handleStatusChange = async (reservation: Reservation, status: string) => {
    try {
      const res = await api.put(`/api/apps/${appId}/reservations/${reservation.id}`, { status })
      setReservations((prev) => prev.map((r) => (r.id === reservation.id ? res.data : r)))
    } catch {
      toast.error('Erro ao atualizar reserva')
    }
  }

  const handleTableSave = async (reservation: Reservation) => {
    const tableNumber = tableDrafts[reservation.id]
    if (tableNumber === undefined) return
    try {
      const res = await api.put(`/api/apps/${appId}/reservations/${reservation.id}`, { table_number: tableNumber })
      setReservations((prev) => prev.map((r) => (r.id === reservation.id ? res.data : r)))
      toast.success('Mesa atribuída!')
    } catch {
      toast.error('Erro ao salvar mesa')
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  if (reservations.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        Nenhuma reserva recebida ainda. Teste o formulário na aba Preview.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">Reservas recebidas ({reservations.length})</p>
      {reservations.map((r) => (
        <div key={r.id} className="border border-gray-200 rounded-lg p-3 text-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="font-medium text-gray-900">
              {new Date(r.reservation_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}
            </p>
            <select
              value={r.status}
              onChange={(e) => handleStatusChange(r, e.target.value)}
              className={`text-xs border-0 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-600 ${STATUS_COLORS[r.status] || ''}`}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <p className="text-gray-700">
            {r.customer_name} · {r.customer_phone} · {r.party_size} pessoa(s)
          </p>
          {r.notes && <p className="text-gray-500 text-xs">Obs: {r.notes}</p>}
          <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
            <input
              type="text"
              value={tableDrafts[r.id] ?? r.table_number ?? ''}
              onChange={(e) => setTableDrafts({ ...tableDrafts, [r.id]: e.target.value })}
              placeholder="Nº da mesa"
              className="w-24 px-2 py-1 text-xs border border-gray-300 rounded"
            />
            <button
              type="button"
              onClick={() => handleTableSave(r)}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Salvar mesa
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
