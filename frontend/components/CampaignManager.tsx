'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

interface Campaign {
  id: number
  channel: 'push' | 'email'
  segment: 'all' | 'customers' | 'non_customers'
  title: string
  body: string
  recipient_count: number
  sent_at: string
}

const SEGMENT_LABELS: Record<string, string> = {
  all: 'Todos os clientes',
  customers: 'Já compraram',
  non_customers: 'Nunca compraram',
}

const CHANNEL_LABELS: Record<string, string> = {
  push: 'Push',
  email: 'E-mail',
}

export default function CampaignManager({ appId }: { appId: string }) {
  const [channel, setChannel] = useState<'push' | 'email'>('push')
  const [segment, setSegment] = useState<'all' | 'customers' | 'non_customers'>('all')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)

  const [history, setHistory] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)

  const fetchHistory = async () => {
    try {
      const res = await api.get<Campaign[]>(`/api/apps/${appId}/campaigns`)
      setHistory(res.data)
    } catch {
      toast.error('Erro ao carregar histórico de campanhas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const handleSend = async () => {
    setSending(true)
    try {
      const res = await api.post<Campaign>(`/api/apps/${appId}/campaigns`, { channel, segment, title, body })
      setHistory([res.data, ...history])
      toast.success(`Campanha enviada para ${res.data.recipient_count} destinatário(s)!`)
      setTitle('')
      setBody('')
    } catch (error: any) {
      showApiError(error, 'Erro ao enviar campanha')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Campanha segmentada</h3>
        <p className="text-sm text-gray-500 mt-1">
          Mande push ou e-mail só pra um recorte dos seus clientes finais (login_cadastro).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Canal</label>
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value as 'push' | 'email')}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
          >
            <option value="push">Push</option>
            <option value="email">E-mail</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Segmento</label>
          <select
            value={segment}
            onChange={(e) => setSegment(e.target.value as 'all' | 'customers' | 'non_customers')}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
          >
            <option value="all">Todos os clientes</option>
            <option value="customers">Já compraram</option>
            <option value="non_customers">Nunca compraram</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {channel === 'email' ? 'Assunto' : 'Título'}
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={channel === 'email' ? 'Promoção especial pra você' : 'Novidade!'}
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
        disabled={sending || !title.trim() || !body.trim()}
        className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {sending ? 'Enviando...' : 'Enviar campanha'}
      </button>

      <hr className="border-gray-200" />

      {loading ? (
        <p className="text-sm text-gray-500">Carregando...</p>
      ) : history.length === 0 ? (
        <p className="text-sm text-gray-400 italic">Nenhuma campanha enviada ainda.</p>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Histórico de campanhas</p>
          {history.map((c) => (
            <div key={c.id} className="border border-gray-200 rounded-lg p-3 text-sm">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-400">{new Date(c.sent_at).toLocaleString('pt-BR')}</p>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                  {CHANNEL_LABELS[c.channel]} · {SEGMENT_LABELS[c.segment]}
                </span>
              </div>
              <p className="text-gray-900 font-medium mt-1">{c.title}</p>
              <p className="text-gray-600">{c.body}</p>
              <p className="text-xs text-gray-500 mt-1">{c.recipient_count} destinatário(s)</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
