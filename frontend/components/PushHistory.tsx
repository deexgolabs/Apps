'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface PushSendLogEntry {
  id: number
  title: string | null
  body: string | null
  sent_at: string
}

export default function PushHistory({ appId }: { appId: string }) {
  const [history, setHistory] = useState<PushSendLogEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await api.get(`/api/apps/${appId}/push/history`)
        setHistory(response.data)
      } catch (error) {
        toast.error('Erro ao carregar histórico de envios')
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [appId])

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  if (history.length === 0) {
    return <p className="text-sm text-gray-400 italic">Nenhuma notificação enviada ainda.</p>
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-gray-700">Histórico de envios</p>
      {history.map((entry) => (
        <div key={entry.id} className="border border-gray-200 rounded-lg p-3 text-sm">
          <p className="text-xs text-gray-400 mb-1">{new Date(entry.sent_at).toLocaleString('pt-BR')}</p>
          <p className="text-gray-900 font-medium">{entry.title || '(sem título)'}</p>
          {entry.body && <p className="text-gray-600">{entry.body}</p>}
        </div>
      ))}
    </div>
  )
}
