'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface EndUser {
  id: number
  email: string
  full_name: string
  created_at: string
}

export default function EndUsersList({ appId }: { appId: string }) {
  const [endUsers, setEndUsers] = useState<EndUser[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchEndUsers = async () => {
      try {
        const response = await api.get(`/api/apps/${appId}/end-users/`)
        setEndUsers(response.data)
      } catch (error) {
        toast.error('Erro ao carregar usuários cadastrados')
      } finally {
        setLoading(false)
      }
    }
    fetchEndUsers()
  }, [appId])

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  if (endUsers.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        Nenhum cliente cadastrado ainda. Teste o cadastro na aba Preview.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">Clientes cadastrados ({endUsers.length})</p>
      {endUsers.map((user) => (
        <div key={user.id} className="border border-gray-200 rounded-lg p-3 text-sm">
          <p className="font-medium text-gray-900">{user.full_name}</p>
          <p className="text-gray-600">{user.email}</p>
          <p className="text-xs text-gray-400 mt-1">
            Cadastrado em {new Date(user.created_at).toLocaleString('pt-BR')}
          </p>
        </div>
      ))}
    </div>
  )
}
