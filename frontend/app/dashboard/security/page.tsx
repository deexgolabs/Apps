'use client'

import { useState } from 'react'
import Link from 'next/link'
import { QRCodeSVG } from 'qrcode.react'
import api from '@/lib/api'
import { useAuthStore } from '@/store/useAuthStore'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

export default function SecurityPage() {
  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)

  const [setupData, setSetupData] = useState<{ secret: string; otpauth_url: string } | null>(null)
  const [code, setCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null)
  const [disablePassword, setDisablePassword] = useState('')
  const [loading, setLoading] = useState(false)

  const startSetup = async () => {
    setLoading(true)
    try {
      const response = await api.post('/api/auth/2fa/setup')
      setSetupData(response.data)
    } catch (error) {
      showApiError(error, 'Erro ao iniciar configuração do 2FA')
    } finally {
      setLoading(false)
    }
  }

  const confirmEnable = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/auth/2fa/enable', { code })
      setRecoveryCodes(response.data.recovery_codes)
      setSetupData(null)
      setCode('')
      if (user) setUser({ ...user, totp_enabled: true })
      toast.success('2FA ativado!')
    } catch (error) {
      showApiError(error, 'Código inválido')
    } finally {
      setLoading(false)
    }
  }

  const disable2fa = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/api/auth/2fa/disable', { password: disablePassword })
      setDisablePassword('')
      if (user) setUser({ ...user, totp_enabled: false })
      toast.success('2FA desativado')
    } catch (error) {
      showApiError(error, 'Senha incorreta')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="py-12 px-4">
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Segurança</h1>
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700">
            ← Voltar
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Verificação em duas etapas (2FA)</h2>
          <p className="text-sm text-gray-600">
            Exige um código do seu app autenticador (Google Authenticator, Authy, etc.)
            além da senha pra entrar na sua conta.
          </p>

          {recoveryCodes ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 space-y-3">
              <p className="text-sm font-semibold text-yellow-900">
                Guarde estes códigos de recuperação — cada um só funciona uma vez e é a única forma de entrar se você perder o acesso ao autenticador.
              </p>
              <div className="grid grid-cols-2 gap-2 font-mono text-sm text-gray-800">
                {recoveryCodes.map((rc) => (
                  <span key={rc} className="bg-white rounded px-2 py-1 border border-gray-200">{rc}</span>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setRecoveryCodes(null)}
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Já guardei, fechar
              </button>
            </div>
          ) : user?.totp_enabled ? (
            <>
              <p className="text-sm font-medium text-green-700">✓ 2FA ativado na sua conta</p>
              <form onSubmit={disable2fa} className="space-y-3">
                <input
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  required
                  placeholder="Digite sua senha pra desativar"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="text-sm border border-red-300 text-red-700 rounded-lg py-2 px-4 hover:bg-red-50 disabled:opacity-50 transition"
                >
                  {loading ? 'Aguarde...' : 'Desativar 2FA'}
                </button>
              </form>
            </>
          ) : setupData ? (
            <form onSubmit={confirmEnable} className="space-y-4">
              <div className="flex justify-center">
                <QRCodeSVG value={setupData.otpauth_url} size={180} />
              </div>
              <p className="text-xs text-gray-500 text-center">
                Escaneie com seu app autenticador, ou digite manualmente: <span className="font-mono">{setupData.secret}</span>
              </p>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                autoFocus
                placeholder="Código de 6 dígitos"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
              >
                {loading ? 'Confirmando...' : 'Confirmar e ativar'}
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={startSetup}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {loading ? 'Aguarde...' : 'Ativar 2FA'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
