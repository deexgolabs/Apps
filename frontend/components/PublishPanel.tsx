'use client'

import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import type { App } from '@/types'

interface PublishPanelProps {
  app: App
  onUpdated: (app: App) => void
}

export default function PublishPanel({ app, onUpdated }: PublishPanelProps) {
  const [saving, setSaving] = useState(false)
  const isPublished = app.status === 'published'
  const publicUrl = typeof window !== 'undefined' ? `${window.location.origin}/app/${app.id}` : ''

  const togglePublish = async () => {
    setSaving(true)
    try {
      const response = await api.put(`/api/apps/${app.id}`, {
        status: isPublished ? 'draft' : 'published',
      })
      onUpdated(response.data)
      toast.success(isPublished ? 'Aplicativo despublicado' : 'Aplicativo publicado!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar status')
    } finally {
      setSaving(false)
    }
  }

  const copyUrl = () => {
    navigator.clipboard.writeText(publicUrl)
    toast.success('Link copiado!')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between p-4 rounded-lg border border-gray-200">
        <div>
          <p className="text-sm font-medium text-gray-700">Status</p>
          <p className={`text-sm ${isPublished ? 'text-green-600' : 'text-gray-500'}`}>
            {isPublished ? '● Publicado' : '○ Rascunho'}
          </p>
        </div>
        <button
          type="button"
          onClick={togglePublish}
          disabled={saving}
          className={`px-4 py-2 rounded-lg font-semibold transition disabled:opacity-50 ${
            isPublished
              ? 'border border-red-300 text-red-600 hover:bg-red-50'
              : 'bg-indigo-600 text-white hover:bg-indigo-700'
          }`}
        >
          {saving ? 'Aguarde...' : isPublished ? 'Despublicar' : 'Publicar'}
        </button>
      </div>

      {isPublished && (
        <div className="text-center space-y-4 p-6 rounded-lg border border-gray-200">
          <div className="flex justify-center bg-white p-4 rounded-lg inline-block">
            <QRCodeSVG value={publicUrl} size={192} />
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-2">Link público do aplicativo</p>
            <div className="flex items-center gap-2 justify-center">
              <a
                href={publicUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:underline text-sm break-all"
              >
                {publicUrl}
              </a>
              <button
                type="button"
                onClick={copyUrl}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 shrink-0"
              >
                Copiar
              </button>
            </div>
          </div>
        </div>
      )}

      {!isPublished && (
        <p className="text-sm text-gray-500 text-center">
          Publique o aplicativo para gerar o link público e o QR code de instalação.
        </p>
      )}
    </div>
  )
}
