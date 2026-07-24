'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface AdminUser {
  id: number
  email: string
  full_name: string
  plan: string
  is_active: boolean
  is_admin: boolean
  is_verified: boolean
  created_at: string
  app_count: number
}

interface AdminApp {
  id: number
  name: string
  status: string
  template_type: string
  owner_email: string
  created_at: string
}

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[] | null>(null)
  const [apps, setApps] = useState<AdminApp[] | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [usersRes, appsRes] = await Promise.all([
          api.get('/api/admin/users'),
          api.get('/api/admin/apps'),
        ])
        setUsers(usersRes.data)
        setApps(appsRes.data)
      } catch (error: any) {
        if (error.response?.status === 403) {
          setForbidden(true)
        } else {
          toast.error('Erro ao carregar painel de administração')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const updateUser = async (id: number, payload: { plan?: string; is_admin?: boolean; is_active?: boolean }) => {
    try {
      const response = await api.put(`/api/admin/users/${id}`, payload)
      setUsers((prev) => prev?.map((u) => (u.id === id ? response.data : u)) || null)
      toast.success('Usuário atualizado')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar usuário')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-gray-600">Carregando...</p>
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <p className="text-gray-600">Acesso negado — esta área é restrita a administradores.</p>
        <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700 font-semibold">
          Voltar ao painel
        </Link>
      </div>
    )
  }

  return (
    <div className="py-12 px-4">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Administração</h1>
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700">
            ← Voltar
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow p-6 overflow-x-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Usuários ({users?.length ?? 0})</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="py-2 pr-4">Nome</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Plano</th>
                <th className="py-2 pr-4">Apps</th>
                <th className="py-2 pr-4">Verificado</th>
                <th className="py-2 pr-4">Admin</th>
                <th className="py-2 pr-4">Ativo</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((u) => (
                <tr key={u.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{u.full_name}</td>
                  <td className="py-2 pr-4">{u.email}</td>
                  <td className="py-2 pr-4">
                    <select
                      value={u.plan}
                      onChange={(e) => updateUser(u.id, { plan: e.target.value })}
                      className="border border-gray-300 rounded px-2 py-1"
                    >
                      <option value="free">free</option>
                      <option value="pro">pro</option>
                      <option value="business">business</option>
                    </select>
                  </td>
                  <td className="py-2 pr-4">{u.app_count}</td>
                  <td className="py-2 pr-4">{u.is_verified ? '✓' : '—'}</td>
                  <td className="py-2 pr-4">
                    <input
                      type="checkbox"
                      checked={u.is_admin}
                      onChange={(e) => updateUser(u.id, { is_admin: e.target.checked })}
                    />
                  </td>
                  <td className="py-2 pr-4">
                    <input
                      type="checkbox"
                      checked={u.is_active}
                      onChange={(e) => updateUser(u.id, { is_active: e.target.checked })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-lg shadow p-6 overflow-x-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Apps ({apps?.length ?? 0})</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="py-2 pr-4">Nome</th>
                <th className="py-2 pr-4">Dono</th>
                <th className="py-2 pr-4">Template</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Criado em</th>
              </tr>
            </thead>
            <tbody>
              {apps?.map((a) => (
                <tr key={a.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{a.name}</td>
                  <td className="py-2 pr-4">{a.owner_email}</td>
                  <td className="py-2 pr-4">{a.template_type}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      a.status === 'published' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4">{new Date(a.created_at).toLocaleDateString('pt-BR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
