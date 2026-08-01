'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface RfmCustomer {
  end_user_id: number
  end_user_name: string
  end_user_email: string
  recency_days: number
  frequency: number
  monetary: number
  tier: string
}

interface RfmSummaryData {
  customers: RfmCustomer[]
  tier_counts: Record<string, number>
}

const TIER_LABELS: Record<string, string> = {
  campeao: 'Campeão',
  em_risco: 'Em risco',
  novo: 'Novo',
  perdido: 'Perdido',
  regular: 'Regular',
}

const TIER_COLORS: Record<string, string> = {
  campeao: 'bg-green-100 text-green-700',
  em_risco: 'bg-yellow-100 text-yellow-700',
  novo: 'bg-blue-100 text-blue-700',
  perdido: 'bg-red-100 text-red-700',
  regular: 'bg-gray-100 text-gray-600',
}

export default function RfmPanel({ appId }: { appId: string }) {
  const [data, setData] = useState<RfmSummaryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get(`/api/apps/${appId}/rfm`)
      .then((res) => setData(res.data))
      .catch(() => toast.error('Erro ao carregar segmentação de clientes'))
      .finally(() => setLoading(false))
  }, [appId])

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Segmentação de clientes (RFM)</h3>
        <p className="text-sm text-gray-500 mt-1">
          Recência, frequência e valor gasto — baseado em pedidos concluídos.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Carregando...</p>
      ) : !data || data.customers.length === 0 ? (
        <p className="text-sm text-gray-400 italic">Nenhum cliente com pedido concluído ainda.</p>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.tier_counts)
              .filter(([, count]) => count > 0)
              .map(([tier, count]) => (
                <span key={tier} className={`text-xs px-2 py-1 rounded ${TIER_COLORS[tier] || 'bg-gray-100 text-gray-600'}`}>
                  {TIER_LABELS[tier] || tier}: {count}
                </span>
              ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-1.5 pr-2">Cliente</th>
                  <th className="py-1.5 pr-2 text-right">Última compra</th>
                  <th className="py-1.5 pr-2 text-right">Pedidos</th>
                  <th className="py-1.5 pr-2 text-right">Total gasto</th>
                  <th className="py-1.5 text-right">Segmento</th>
                </tr>
              </thead>
              <tbody>
                {data.customers.map((c) => (
                  <tr key={c.end_user_id} className="border-b border-gray-100 last:border-0">
                    <td className="py-1.5 pr-2 text-gray-700">
                      <div>{c.end_user_name}</div>
                      <div className="text-xs text-gray-400">{c.end_user_email}</div>
                    </td>
                    <td className="py-1.5 pr-2 text-right text-gray-500">{c.recency_days}d atrás</td>
                    <td className="py-1.5 pr-2 text-right text-gray-500">{c.frequency}</td>
                    <td className="py-1.5 pr-2 text-right text-gray-700 font-medium">R$ {c.monetary.toFixed(2)}</td>
                    <td className="py-1.5 text-right">
                      <span className={`text-xs px-2 py-0.5 rounded ${TIER_COLORS[c.tier] || 'bg-gray-100 text-gray-600'}`}>
                        {TIER_LABELS[c.tier] || c.tier}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
