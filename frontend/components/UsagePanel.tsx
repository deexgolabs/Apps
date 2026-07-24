'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface UsageEntry {
  used: number
  limit: number
}

interface UsageData {
  items: UsageEntry
  categories: UsageEntry
  push_sends_this_month: UsageEntry
}

const LABELS: Record<keyof UsageData, string> = {
  items: 'Itens cadastrados',
  categories: 'Categorias',
  push_sends_this_month: 'Envios de push este mês',
}

export default function UsagePanel({ appId }: { appId: string }) {
  const [usage, setUsage] = useState<UsageData | null>(null)

  useEffect(() => {
    api.get(`/api/apps/${appId}/usage`).then((res) => setUsage(res.data)).catch(() => {})
  }, [appId])

  if (!usage) return null

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
      <p className="text-sm font-medium text-gray-700">Uso do plano</p>
      {(Object.keys(LABELS) as (keyof UsageData)[]).map((key) => {
        const { used, limit } = usage[key]
        const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : used > 0 ? 100 : 0
        return (
          <div key={key}>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{LABELS[key]}</span>
              <span>{used} / {limit}</span>
            </div>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div className={`h-full ${pct >= 100 ? 'bg-red-500' : 'bg-indigo-600'}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
