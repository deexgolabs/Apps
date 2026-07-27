'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface SalesReportProduct {
  name: string
  quantity: number
  revenue: number
}

interface SalesReportData {
  revenue: number
  orders_by_status: Record<string, number>
  top_products: SalesReportProduct[]
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  confirmed: 'Confirmado',
  preparing: 'Preparando',
  completed: 'Concluído',
  cancelled: 'Cancelado',
}

const PERIODS = [
  { value: '7', label: 'Últimos 7 dias' },
  { value: '30', label: 'Últimos 30 dias' },
  { value: '90', label: 'Últimos 90 dias' },
  { value: '', label: 'Todo o período' },
]

export default function SalesReport({ appId }: { appId: string }) {
  const [period, setPeriod] = useState('30')
  const [data, setData] = useState<SalesReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .get(`/api/apps/${appId}/orders/report`, { params: period ? { days: period } : {} })
      .then((res) => setData(res.data))
      .catch(() => toast.error('Erro ao carregar relatório'))
      .finally(() => setLoading(false))
  }, [appId, period])

  const handleExportCsv = async () => {
    setExporting(true)
    try {
      const response = await api.get(`/api/apps/${appId}/orders/export.csv`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `pedidos_app_${appId}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      toast.error('Erro ao exportar CSV')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
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
        <button
          type="button"
          onClick={handleExportCsv}
          disabled={exporting}
          className="text-sm bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-50"
        >
          {exporting ? 'Exportando...' : '⬇ Exportar CSV'}
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Carregando...</p>
      ) : !data ? (
        <p className="text-sm text-gray-400 italic">Não foi possível carregar o relatório.</p>
      ) : (
        <div className="space-y-4">
          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
            <p className="text-xs text-indigo-600 font-medium">Receita (pedidos concluídos)</p>
            <p className="text-2xl font-bold text-indigo-900">R$ {data.revenue.toFixed(2)}</p>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Pedidos por status</p>
            {Object.keys(data.orders_by_status).length === 0 ? (
              <p className="text-sm text-gray-400 italic">Nenhum pedido no período.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {Object.entries(data.orders_by_status).map(([status, count]) => (
                  <span key={status} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    {STATUS_LABELS[status] || status}: {count}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Produtos mais vendidos</p>
            {data.top_products.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Nenhum produto vendido no período.</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {data.top_products.map((p) => (
                    <tr key={p.name} className="border-b border-gray-100 last:border-0">
                      <td className="py-1.5 text-gray-700">{p.name}</td>
                      <td className="py-1.5 text-right text-gray-500">{p.quantity}x</td>
                      <td className="py-1.5 text-right text-gray-700 font-medium">R$ {p.revenue.toFixed(2)}</td>
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
