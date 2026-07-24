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

interface PlanConfig {
  plan_name: string
  price: number
  max_apps: number
  max_modules: number
  max_items: number
  max_categories: number
  max_push_sends_per_month: number
}

interface AuditLogEntry {
  id: number
  admin_email: string
  action: string
  target: string
  details: string | null
  created_at: string
}

interface Stats {
  mrr: number
  published_apps: number
  total_apps: number
  users_by_plan: Record<string, number>
}

const STATUS_LABELS: Record<string, string> = {
  published: 'Publicado',
  draft: 'Rascunho',
  suspended: 'Suspenso',
}

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[] | null>(null)
  const [apps, setApps] = useState<AdminApp[] | null>(null)
  const [plans, setPlans] = useState<PlanConfig[] | null>(null)
  const [planEdits, setPlanEdits] = useState<Record<string, PlanConfig>>({})
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[] | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchAll = async () => {
    try {
      const [usersRes, appsRes, plansRes, auditRes, statsRes] = await Promise.all([
        api.get('/api/admin/users'),
        api.get('/api/admin/apps'),
        api.get('/api/admin/plans'),
        api.get('/api/admin/audit-logs'),
        api.get('/api/admin/stats'),
      ])
      setUsers(usersRes.data)
      setApps(appsRes.data)
      setPlans(plansRes.data)
      setPlanEdits(Object.fromEntries(plansRes.data.map((p: PlanConfig) => [p.plan_name, p])))
      setAuditLogs(auditRes.data)
      setStats(statsRes.data)
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

  useEffect(() => {
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const savePlan = async (planName: string) => {
    const edit = planEdits[planName]
    if (!edit) return
    try {
      const response = await api.put(`/api/admin/plans/${planName}`, {
        price: edit.price,
        max_apps: edit.max_apps,
        max_modules: edit.max_modules,
        max_items: edit.max_items,
        max_categories: edit.max_categories,
        max_push_sends_per_month: edit.max_push_sends_per_month,
      })
      setPlans((prev) => prev?.map((p) => (p.plan_name === planName ? response.data : p)) || null)
      toast.success(`Plano ${planName} atualizado`)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar plano')
    }
  }

  const suspendApp = async (id: number, currentStatus: string) => {
    const newStatus = currentStatus === 'suspended' ? 'draft' : 'suspended'
    try {
      const response = await api.put(`/api/admin/apps/${id}/status`, { status: newStatus })
      setApps((prev) => prev?.map((a) => (a.id === id ? response.data : a)) || null)
      toast.success(newStatus === 'suspended' ? 'App suspenso' : 'App reativado')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar status do app')
    }
  }

  const deleteApp = async (id: number, name: string) => {
    if (!confirm(`Excluir definitivamente o app "${name}"? Essa ação não pode ser desfeita.`)) return
    try {
      await api.delete(`/api/admin/apps/${id}`)
      setApps((prev) => prev?.filter((a) => a.id !== id) || null)
      toast.success('App excluído')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao excluir app')
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

        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Receita mensal estimada (MRR)</p>
              <p className="text-2xl font-bold text-gray-900">R$ {stats.mrr.toFixed(2)}</p>
              <p className="text-xs text-gray-400 mt-1">Soma do preço do plano de cada usuário ativo</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Apps publicados</p>
              <p className="text-2xl font-bold text-gray-900">{stats.published_apps}</p>
              <p className="text-xs text-gray-400 mt-1">de {stats.total_apps} no total</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Usuários por plano</p>
              <p className="text-sm text-gray-900 mt-1">
                {Object.entries(stats.users_by_plan)
                  .map(([plan, count]) => `${plan}: ${count}`)
                  .join(' · ') || '—'}
              </p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6 overflow-x-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Planos</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="py-2 pr-4">Plano</th>
                <th className="py-2 pr-4">Preço (R$)</th>
                <th className="py-2 pr-4">Apps</th>
                <th className="py-2 pr-4">Módulos</th>
                <th className="py-2 pr-4">Itens</th>
                <th className="py-2 pr-4">Categorias</th>
                <th className="py-2 pr-4">Push/mês</th>
                <th className="py-2 pr-4"></th>
              </tr>
            </thead>
            <tbody>
              {plans?.map((p) => {
                const edit = planEdits[p.plan_name] || p
                const setField = (field: keyof PlanConfig, value: number) =>
                  setPlanEdits((prev) => ({ ...prev, [p.plan_name]: { ...edit, [field]: value } }))
                return (
                  <tr key={p.plan_name} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-medium">{p.plan_name}</td>
                    {(['price', 'max_apps', 'max_modules', 'max_items', 'max_categories', 'max_push_sends_per_month'] as const).map((field) => (
                      <td key={field} className="py-2 pr-4">
                        <input
                          type="number"
                          value={edit[field]}
                          onChange={(e) => setField(field, Number(e.target.value))}
                          className="w-20 border border-gray-300 rounded px-2 py-1"
                        />
                      </td>
                    ))}
                    <td className="py-2 pr-4">
                      <button
                        type="button"
                        onClick={() => savePlan(p.plan_name)}
                        className="text-indigo-600 hover:text-indigo-700 font-medium"
                      >
                        Salvar
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
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
                <th className="py-2 pr-4"></th>
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
                      a.status === 'published'
                        ? 'bg-green-100 text-green-800'
                        : a.status === 'suspended'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {STATUS_LABELS[a.status] || a.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4">{new Date(a.created_at).toLocaleDateString('pt-BR')}</td>
                  <td className="py-2 pr-4 flex gap-3">
                    <button
                      type="button"
                      onClick={() => suspendApp(a.id, a.status)}
                      className="text-yellow-600 hover:text-yellow-700 font-medium"
                    >
                      {a.status === 'suspended' ? 'Reativar' : 'Suspender'}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteApp(a.id, a.name)}
                      className="text-red-600 hover:text-red-700 font-medium"
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-lg shadow p-6 overflow-x-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Log de auditoria (últimos {auditLogs?.length ?? 0})</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="py-2 pr-4">Quando</th>
                <th className="py-2 pr-4">Admin</th>
                <th className="py-2 pr-4">Ação</th>
                <th className="py-2 pr-4">Alvo</th>
                <th className="py-2 pr-4">Detalhes</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs?.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-gray-400 italic">Nenhuma ação registrada ainda.</td>
                </tr>
              ) : (
                auditLogs?.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100">
                    <td className="py-2 pr-4 whitespace-nowrap">{new Date(log.created_at).toLocaleString('pt-BR')}</td>
                    <td className="py-2 pr-4">{log.admin_email}</td>
                    <td className="py-2 pr-4">{log.action}</td>
                    <td className="py-2 pr-4">{log.target}</td>
                    <td className="py-2 pr-4 text-gray-500">{log.details}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
