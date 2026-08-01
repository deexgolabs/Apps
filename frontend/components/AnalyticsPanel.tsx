'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface AnalyticsSummaryModule {
  module_name: string
  views: number
}

interface AnalyticsSummaryData {
  total_views: number
  unique_visitors: number
  top_modules: AnalyticsSummaryModule[]
}

const PERIODS = [
  { value: '7', label: 'Últimos 7 dias' },
  { value: '30', label: 'Últimos 30 dias' },
  { value: '90', label: 'Últimos 90 dias' },
  { value: '', label: 'Todo o período' },
]

export default function AnalyticsPanel({ appId }: { appId: string }) {
  const [period, setPeriod] = useState('30')
  const [data, setData] = useState<AnalyticsSummaryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api
      .get(`/api/apps/${appId}/analytics/summary`, { params: period ? { days: period } : {} })
      .then((res) => setData(res.data))
      .catch(() => toast.error('Erro ao carregar analytics'))
      .finally(() => setLoading(false))
  }, [appId, period])

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Visitantes</h3>
        <p className="text-sm text-gray-500 mt-1">
          Visitas anônimas ao seu app publicado — sem rastrear dados pessoais.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-gray-700">Período</label>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-600"
        >
          {PERIODS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Carregando...</p>
      ) : !data ? (
        <p className="text-sm text-gray-400 italic">Não foi possível carregar os dados de visitas.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
              <p className="text-xs text-indigo-600 font-medium">Visualizações</p>
              <p className="text-2xl font-bold text-indigo-900">{data.total_views}</p>
            </div>
            <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
              <p className="text-xs text-indigo-600 font-medium">Visitantes únicos</p>
              <p className="text-2xl font-bold text-indigo-900">{data.unique_visitors}</p>
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Módulos mais visitados</p>
            {data.top_modules.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Nenhuma visita registrada no período.</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {data.top_modules.map((m) => (
                    <tr key={m.module_name} className="border-b border-gray-100 last:border-0">
                      <td className="py-1.5 text-gray-700">{m.module_name}</td>
                      <td className="py-1.5 text-right text-gray-500">{m.views} visita(s)</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
