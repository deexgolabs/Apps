'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

interface WebhookSubscription {
  id: number
  url: string
  event: string
  secret: string
  active: boolean
  created_at: string
}

const EVENT_OPTIONS: { value: string; label: string }[] = [
  { value: 'order.created', label: 'Novo pedido' },
  { value: 'order.status_changed', label: 'Status do pedido mudou' },
  { value: '*', label: 'Todos os eventos' },
]

const EVENT_LABELS: Record<string, string> = Object.fromEntries(EVENT_OPTIONS.map((o) => [o.value, o.label]))

export default function WebhooksManager({ appId }: { appId: string }) {
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  const [url, setUrl] = useState('')
  const [event, setEvent] = useState('order.created')

  const fetchWebhooks = async () => {
    try {
      const res = await api.get<WebhookSubscription[]>(`/api/apps/${appId}/webhooks/subscriptions`)
      setWebhooks(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWebhooks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const handleCreate = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!url.trim()) return
    try {
      const res = await api.post(`/api/apps/${appId}/webhooks/subscriptions`, { url, event })
      setWebhooks([res.data, ...webhooks])
      setUrl('')
      setEvent('order.created')
      toast.success('Webhook criado!')
    } catch (error: any) {
      showApiError(error, 'Erro ao criar webhook')
    }
  }

  const handleToggleActive = async (webhook: WebhookSubscription) => {
    try {
      const res = await api.put(`/api/apps/${appId}/webhooks/subscriptions/${webhook.id}`, { active: !webhook.active })
      setWebhooks(webhooks.map((w) => (w.id === webhook.id ? res.data : w)))
    } catch {
      toast.error('Erro ao atualizar webhook')
    }
  }

  const handleDelete = async (webhookId: number) => {
    try {
      await api.delete(`/api/apps/${appId}/webhooks/subscriptions/${webhookId}`)
      setWebhooks(webhooks.filter((w) => w.id !== webhookId))
    } catch {
      toast.error('Erro ao remover webhook')
    }
  }

  const copySecret = async (secret: string) => {
    await navigator.clipboard.writeText(secret)
    toast.success('Segredo copiado!')
  }

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700"
      >
        <span>Webhooks de saída {webhooks.length > 0 && `(${webhooks.length})`}</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-3 border-t border-gray-200 space-y-3">
          <p className="text-xs text-gray-500">
            Receba uma notificação HTTP no seu próprio sistema quando um pedido for criado ou mudar de status.
            Cada envio é assinado (header <code>X-Webhook-Signature</code>, HMAC-SHA256 com o segredo abaixo)
            pra você conferir que veio mesmo da plataforma.
          </p>
          {loading ? (
            <p className="text-sm text-gray-500">Carregando...</p>
          ) : (
            <>
              {/* Não usa <form> aqui de propósito: este painel renderiza dentro do
                  <form> maior da página (aba "Pedidos" faz parte do form de salvar
                  o app inteiro) — um <form> aninhado faz o clique disparar o submit
                  do form de fora em vez deste, então o botão é type="button" + onClick. */}
              <div className="space-y-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://seusite.com/webhook"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                />
                <select
                  value={event}
                  onChange={(e) => setEvent(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                >
                  {EVENT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleCreate()}
                  className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700"
                >
                  + Adicionar webhook
                </button>
              </div>

              <div className="space-y-1.5">
                {webhooks.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">Nenhum webhook configurado ainda</p>
                ) : (
                  webhooks.map((w) => (
                    <div key={w.id} className="border border-gray-200 rounded-lg px-3 py-2 text-sm space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900 truncate">{w.url}</p>
                          <p className="text-xs text-gray-500">{EVENT_LABELS[w.event] || w.event}</p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            type="button"
                            onClick={() => handleToggleActive(w)}
                            className={`text-xs px-2 py-1 rounded ${
                              w.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            {w.active ? 'Ativo' : 'Inativo'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(w.id)}
                            className="text-gray-400 hover:text-red-600"
                            aria-label={`Remover webhook ${w.url}`}
                          >
                            ×
                          </button>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <code className="text-xs text-gray-400 truncate">{w.secret}</code>
                        <button
                          type="button"
                          onClick={() => copySecret(w.secret)}
                          className="text-xs text-indigo-600 hover:text-indigo-700 flex-shrink-0"
                        >
                          Copiar segredo
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
