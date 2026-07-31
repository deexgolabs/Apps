'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'
import { useAuthStore } from '@/store/useAuthStore'

interface Collaborator {
  id: number
  user_id: number
  email: string
  full_name: string
  role: 'editor' | 'viewer'
  created_at: string
}

const ROLE_LABELS: Record<string, string> = {
  editor: 'Editor (pode editar)',
  viewer: 'Visualizador (só ver)',
}

export default function TeamManager({ appId, isOwner }: { appId: string; isOwner: boolean }) {
  const currentUserId = useAuthStore((state) => state.user?.id)
  const [collaborators, setCollaborators] = useState<Collaborator[]>([])
  const [loading, setLoading] = useState(true)

  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'editor' | 'viewer'>('editor')
  const [inviting, setInviting] = useState(false)

  const fetchCollaborators = async () => {
    try {
      const res = await api.get<Collaborator[]>(`/api/apps/${appId}/collaborators`)
      setCollaborators(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCollaborators()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setInviting(true)
    try {
      const res = await api.post(`/api/apps/${appId}/collaborators`, { email: email.trim(), role })
      setCollaborators([...collaborators, res.data])
      setEmail('')
      setRole('editor')
      toast.success('Convidado adicionado à equipe!')
    } catch (error: any) {
      showApiError(error, 'Erro ao convidar')
    } finally {
      setInviting(false)
    }
  }

  const handleRoleChange = async (collaborator: Collaborator, newRole: 'editor' | 'viewer') => {
    try {
      const res = await api.put(`/api/apps/${appId}/collaborators/${collaborator.id}`, { role: newRole })
      setCollaborators(collaborators.map((c) => (c.id === collaborator.id ? res.data : c)))
    } catch (error: any) {
      showApiError(error, 'Erro ao atualizar papel')
    }
  }

  const handleRemove = async (collaborator: Collaborator) => {
    const isSelf = collaborator.user_id === currentUserId
    if (!confirm(isSelf ? 'Sair da equipe deste app?' : `Remover ${collaborator.full_name} da equipe?`)) return
    try {
      await api.delete(`/api/apps/${appId}/collaborators/${collaborator.id}`)
      setCollaborators(collaborators.filter((c) => c.id !== collaborator.id))
      toast.success(isSelf ? 'Você saiu da equipe' : 'Removido da equipe')
    } catch (error: any) {
      showApiError(error, 'Erro ao remover')
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Equipe</h3>
        <p className="text-sm text-gray-500 mt-1">
          Convide outras pessoas pra ajudar a gerenciar este app. Editores podem alterar tudo, exceto
          excluir o app ou gerenciar a equipe; visualizadores só podem ver.
        </p>
      </div>

      {isOwner && (
        <form onSubmit={handleInvite} className="flex flex-col sm:flex-row gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e-mail da pessoa (precisa já ter uma conta)"
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as 'editor' | 'viewer')}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg"
          >
            <option value="editor">Editor</option>
            <option value="viewer">Visualizador</option>
          </select>
          <button
            type="submit"
            disabled={inviting}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
          >
            {inviting ? 'Convidando...' : '+ Convidar'}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Carregando...</p>
      ) : collaborators.length === 0 ? (
        <p className="text-sm text-gray-400 italic">Ninguém além de você tem acesso a este app ainda.</p>
      ) : (
        <div className="space-y-1.5">
          {collaborators.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between gap-2 border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">{c.full_name}</p>
                <p className="text-xs text-gray-500 truncate">{c.email}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {isOwner ? (
                  <select
                    value={c.role}
                    onChange={(e) => handleRoleChange(c, e.target.value as 'editor' | 'viewer')}
                    className="text-xs px-2 py-1 border border-gray-300 rounded"
                  >
                    <option value="editor">Editor</option>
                    <option value="viewer">Visualizador</option>
                  </select>
                ) : (
                  <span className="text-xs text-gray-500">{ROLE_LABELS[c.role] || c.role}</span>
                )}
                {(isOwner || c.user_id === currentUserId) && (
                  <button
                    type="button"
                    onClick={() => handleRemove(c)}
                    className="text-gray-400 hover:text-red-600"
                    aria-label={`Remover ${c.full_name}`}
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
