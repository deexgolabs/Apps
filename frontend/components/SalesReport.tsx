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

interface FinancialBreakdownItem {
  key: string
  count: number
  revenue: number
}

interface FinancialReportData {
  total_revenue: number
  total_delivery_fees: number
  total_discounts: number
  cancelled_count: number
  cancelled_value: number
  by_fulfillment_type: FinancialBreakdownItem[]
  by_payment_method: FinancialBreakdownItem[]
}

const FULFILLMENT_LABELS: Record<string, string> = {
  delivery: 'Entrega',
  pickup: 'Retirada',
  dine_in: 'Mesa/comanda',
}

const PAYMENT_LABELS: Record<string, string> = {
  pagamento_na_entrega: 'Na entrega/retirada',
  mercado_pago: 'Mercado Pago',
  paypal: 'PayPal',
  pagseguro: 'PagSeguro',
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
  const [financialData, setFinancialData] = useState<FinancialReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [exportingFinancial, setExportingFinancial] = useState(false)

  useEffect(() => {
    setLoading(true)
    const params = period ? { days: period } : {}
    Promise.all([
      api.get(`/api/apps/${appId}/orders/report`, { params }),
      api.get(`/api/apps/${appId}/orders/financial-report`, { params }),
    ])
      .then(([reportRes, financialRes]) => {
        setData(reportRes.data)
        setFinancialData(financialRes.data)
      })
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

  const handleExportFinancialCsv = async () => {
    setExportingFinancial(true)
    try {
      const response = await api.get(`/api/apps/${appId}/orders/financial-export.csv`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `financeiro_app_${appId}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      toast.error('Erro ao exportar CSV financeiro')
    } finally {
      setExportingFinancial(false)
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
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exporting}
            className="text-sm bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-50"
          >
            {exporting ? 'Exportando...' : '⬇ Exportar pedidos CSV'}
          </button>
          <button
            type="button"
            onClick={handleExportFinancialCsv}
            disabled={exportingFinancial}
            className="text-sm bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-50"
          >
            {exportingFinancial ? 'Exportando...' : '⬇ Exportar financeiro CSV'}
          </button>
        </div>
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

          {financialData && (
            <div className="space-y-3 border-t border-gray-100 pt-4">
              <p className="text-sm font-medium text-gray-700">Financeiro detalhado</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Frete total</p>
                  <p className="text-sm font-semibold text-gray-900">R$ {financialData.total_delivery_fees.toFixed(2)}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Descontos</p>
                  <p className="text-sm font-semibold text-gray-900">R$ {financialData.total_discounts.toFixed(2)}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Cancelados</p>
                  <p className="text-sm font-semibold text-gray-900">{financialData.cancelled_count}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Valor cancelado</p>
                  <p className="text-sm font-semibold text-gray-900">R$ {financialData.cancelled_value.toFixed(2)}</p>
                </div>
              </div>

              {financialData.by_fulfillment_type.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Por forma de entrega</p>
                  <div className="flex flex-wrap gap-2">
                    {financialData.by_fulfillment_type.map((b) => (
                      <span key={b.key} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                        {FULFILLMENT_LABELS[b.key] || b.key}: {b.count} · R$ {b.revenue.toFixed(2)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {financialData.by_payment_method.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Por forma de pagamento</p>
                  <div className="flex flex-wrap gap-2">
                    {financialData.by_payment_method.map((b) => (
                      <span key={b.key} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                        {PAYMENT_LABELS[b.key] || b.key}: {b.count} · R$ {b.revenue.toFixed(2)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
