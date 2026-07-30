'use client'

import { useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

interface ImportResult {
  name: string | null
  description: string | null
  image_url: string | null
}

interface ImportFromUrlPanelProps {
  appId: string
  onImported: (result: ImportResult) => void
}

export default function ImportFromUrlPanel({ appId, onImported }: ImportFromUrlPanelProps) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)

  const handleImport = async () => {
    if (!url.trim()) return
    setLoading(true)
    try {
      const response = await api.post<ImportResult>(`/api/apps/${appId}/import-from-url`, { url: url.trim() })
      onImported(response.data)
      toast.success('Dados importados! Confira os campos abaixo e clique em Salvar.')
    } catch (error: any) {
      showApiError(error, 'Não foi possível importar dessa URL')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-2 p-4 rounded-lg border border-gray-200">
      <div>
        <p className="text-sm font-medium text-gray-700">Importar de um site ou rede social</p>
        <p className="text-xs text-gray-500">
          Cole o link do seu site, Instagram ou Facebook — a gente busca nome, descrição e imagem automaticamente pra preencher os campos abaixo (você ainda revisa e clica em Salvar).
        </p>
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              handleImport()
            }
          }}
          placeholder="instagram.com/suamarca"
          className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
        />
        <button
          type="button"
          onClick={handleImport}
          disabled={loading}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Importando...' : 'Importar'}
        </button>
      </div>
    </div>
  )
}
