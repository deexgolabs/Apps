'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'
import type { CustomDomainStatus } from '@/types'

export default function CustomDomainPanel({ appId }: { appId: string }) {
  const [status, setStatus] = useState<CustomDomainStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [domainInput, setDomainInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)

  const fetchStatus = async () => {
    try {
      const response = await api.get<CustomDomainStatus>(`/api/apps/${appId}/custom-domain`)
      setStatus(response.data)
      setDomainInput(response.data.domain || '')
    } catch (error) {
      toast.error('Erro ao carregar domínio')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const handleSave = async () => {
    if (!domainInput.trim()) return
    setSaving(true)
    try {
      const response = await api.put<CustomDomainStatus>(`/api/apps/${appId}/custom-domain`, { domain: domainInput.trim() })
      setStatus(response.data)
      toast.success('Domínio salvo! Siga as instruções de DNS abaixo pra verificar.')
    } catch (error: any) {
      showApiError(error, 'Erro ao salvar domínio')
    } finally {
      setSaving(false)
    }
  }

  const handleVerify = async () => {
    setVerifying(true)
    try {
      const response = await api.post<CustomDomainStatus>(`/api/apps/${appId}/custom-domain/verify`)
      setStatus(response.data)
      if (response.data.verified) {
        toast.success('Domínio verificado!')
      }
    } catch (error: any) {
      showApiError(error, 'Ainda não foi possível verificar')
    } finally {
      setVerifying(false)
    }
  }

  const handleRemove = async () => {
    if (!confirm('Remover o domínio próprio deste app?')) return
    try {
      await api.delete(`/api/apps/${appId}/custom-domain`)
      setStatus({ domain: null, verified: false, verification_host: null, verification_token: null })
      setDomainInput('')
      toast.success('Domínio removido')
    } catch (error) {
      toast.error('Erro ao remover domínio')
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  return (
    <div className="space-y-4 p-4 rounded-lg border border-gray-200">
      <div>
        <p className="text-sm font-medium text-gray-700">Domínio próprio</p>
        <p className="text-xs text-gray-500">
          Além do link padrão da plataforma, você pode usar seu próprio domínio (ex: <code>loja.suamarca.com.br</code>) pra acessar este app.
        </p>
      </div>

      {status?.domain && status.verified ? (
        <div className="flex items-center justify-between p-3 rounded-lg bg-green-50 border border-green-200">
          <div>
            <p className="text-sm font-medium text-green-700">✓ {status.domain}</p>
            <p className="text-xs text-green-600">Verificado e ativo</p>
          </div>
          <button
            type="button"
            onClick={handleRemove}
            className="text-xs text-red-600 hover:underline"
          >
            Remover
          </button>
        </div>
      ) : (
        // Não usa <form> aqui de propósito: este painel já renderiza dentro do
        // <form> maior da página (aba "Publicar" faz parte do form de salvar o
        // app inteiro) — um <form> aninhado faz o clique disparar o submit do
        // form de fora em vez deste, então o botão é type="button" + onClick.
        <div className="flex gap-2">
          <input
            type="text"
            value={domainInput}
            onChange={(e) => setDomainInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                handleSave()
              }
            }}
            placeholder="loja.suamarca.com.br"
            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      )}

      {status?.domain && !status.verified && (
        <div className="space-y-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm">
          <p className="text-amber-800 font-medium">Pendente de verificação</p>
          <p className="text-amber-700 text-xs">
            Adicione este registro no DNS do seu domínio (no painel do seu provedor de domínio) e depois clique em "Verificar":
          </p>
          <div className="bg-white rounded border border-amber-200 p-2 text-xs font-mono space-y-1">
            <p>Tipo: <span className="font-semibold">TXT</span></p>
            <p>Nome: <span className="font-semibold break-all">{status.verification_host}</span></p>
            <p>Valor: <span className="font-semibold break-all">{status.verification_token}</span></p>
          </div>
          <p className="text-amber-700 text-xs">
            Além do TXT (só prova que o domínio é seu), aponte também um <span className="font-semibold">CNAME</span> de{' '}
            <span className="font-mono">{status.domain}</span> pra <span className="font-mono">cname.vercel-dns.com</span> — é o que
            faz o tráfego chegar até aqui. A propagação de DNS pode levar de minutos a algumas horas.
          </p>
          <button
            type="button"
            onClick={handleVerify}
            disabled={verifying}
            className="px-3 py-1.5 text-xs bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
          >
            {verifying ? 'Verificando...' : 'Verificar agora'}
          </button>
          <button
            type="button"
            onClick={handleRemove}
            className="ml-2 text-xs text-red-600 hover:underline"
          >
            Cancelar
          </button>
        </div>
      )}
    </div>
  )
}
