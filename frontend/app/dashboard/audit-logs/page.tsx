'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { OwnerAuditLog } from '@/types'

const ACTION_LABELS: Record<string, string> = {
  create_app: 'Criou o app',
  update_app: 'Editou o app',
  update_app_status: 'Mudou o status do app',
  restore_version: 'Restaurou uma versão',
  delete_app: 'Excluiu o app',
  update_order_status: 'Mudou o status de um pedido',
  enable_2fa: 'Ativou o 2FA',
  disable_2fa: 'Desativou o 2FA',
  confirm_billing: 'Confirmou upgrade de plano',
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<OwnerAuditLog[] | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/audit-logs/')
      .then((response) => setLogs(response.data))
      .catch(() => toast.error('Erro ao carregar log de auditoria'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="py-12 px-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Log de Auditoria</h1>
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700">
            ← Voltar
          </Link>
        </div>
        <p className="text-gray-600">
          Histórico das últimas ações na sua conta: criação/edição/publicação/exclusão de apps,
          mudanças de status de pedido, plano e segurança (2FA).
        </p>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <p className="p-6 text-gray-600">Carregando...</p>
          ) : !logs || logs.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">Nenhuma ação registrada ainda.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {logs.map((log) => (
                <li key={log.id} className="p-4 flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-gray-900">
                      {ACTION_LABELS[log.action] || log.action}
                      {log.app_name && <span className="text-gray-500 font-normal"> — {log.app_name}</span>}
                    </p>
                    {log.details && <p className="text-sm text-gray-500 mt-1">{log.details}</p>}
                  </div>
                  <span className="text-xs text-gray-400 shrink-0">
                    {new Date(log.created_at).toLocaleString('pt-BR')}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
