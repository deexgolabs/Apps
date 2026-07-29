'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'
import type { App, AppVersion } from '@/types'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

export default function VersionHistoryPanel({ appId, onRestored }: { appId: string; onRestored: (app: App) => void }) {
  const [versions, setVersions] = useState<AppVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [restoringId, setRestoringId] = useState<number | null>(null)

  const fetchVersions = async () => {
    try {
      const response = await api.get<AppVersion[]>(`/api/apps/${appId}/versions`)
      setVersions(response.data)
    } catch (error) {
      toast.error('Erro ao carregar histórico de versões')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVersions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const handleRestore = async (version: AppVersion) => {
    if (!confirm(`Restaurar o app pro estado de ${formatDate(version.created_at)}? O estado atual vira uma versão nova, então dá pra desfazer depois.`)) return
    setRestoringId(version.id)
    try {
      const response = await api.post<App>(`/api/apps/${appId}/versions/${version.id}/restore`)
      onRestored(response.data)
      toast.success('App restaurado!')
      fetchVersions()
    } catch (error: any) {
      showApiError(error, 'Erro ao restaurar versão')
    } finally {
      setRestoringId(null)
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  return (
    <div className="space-y-3 p-4 rounded-lg border border-gray-200">
      <div>
        <p className="text-sm font-medium text-gray-700">Histórico de versões</p>
        <p className="text-xs text-gray-500">
          Cada alteração salva (nome, descrição, módulos ou config da Marca) guarda o estado anterior aqui — até as últimas 20 versões.
        </p>
      </div>

      {versions.length === 0 ? (
        <p className="text-sm text-gray-400">Nenhuma versão salva ainda. Faça uma alteração e clique em Salvar.</p>
      ) : (
        <ul className="space-y-2 max-h-72 overflow-y-auto">
          {versions.map((version) => (
            <li
              key={version.id}
              className="flex items-center justify-between gap-2 p-2 rounded border border-gray-100 bg-gray-50 text-sm"
            >
              <div className="min-w-0">
                <p className="font-medium text-gray-800 truncate">{version.name}</p>
                <p className="text-xs text-gray-500">{formatDate(version.created_at)} · {version.modules.length} módulo(s)</p>
              </div>
              <button
                type="button"
                onClick={() => handleRestore(version)}
                disabled={restoringId !== null}
                className="shrink-0 px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {restoringId === version.id ? 'Restaurando...' : 'Restaurar'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
