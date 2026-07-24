'use client'

import { useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

export default function PushComposer({ appId }: { appId: string }) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [lastResult, setLastResult] = useState<{ sent: number; failed: number; total: number } | null>(null)

  const handleSend = async () => {
    setSending(true)
    try {
      const response = await api.post(`/api/apps/${appId}/push/send`, { title, body })
      setLastResult(response.data)
      toast.success('Notificação enviada!')
      setTitle('')
      setBody('')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao enviar notificação')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Novidade!"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Mensagem</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Confira nossa promoção de hoje"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 h-20"
        />
      </div>
      <button
        type="button"
        onClick={handleSend}
        disabled={sending || !title || !body}
        className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {sending ? 'Enviando...' : 'Enviar notificação'}
      </button>
      {lastResult && (
        <p className="text-xs text-gray-500 text-center">
          Enviada para {lastResult.sent} de {lastResult.total} inscrito(s).
        </p>
      )}
    </div>
  )
}
