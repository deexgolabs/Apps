'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { ReferralsInfo } from '@/types'

export default function ReferralsPage() {
  const [info, setInfo] = useState<ReferralsInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.get('/api/users/me/referrals')
      .then((response) => setInfo(response.data))
      .catch(() => toast.error('Erro ao carregar programa de indicação'))
      .finally(() => setLoading(false))
  }, [])

  const copyLink = async () => {
    if (!info) return
    await navigator.clipboard.writeText(info.referral_link)
    setCopied(true)
    toast.success('Link copiado!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="py-12 px-4">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Programa de Indicação</h1>
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700">
            ← Voltar
          </Link>
        </div>

        {loading ? (
          <p className="text-gray-600">Carregando...</p>
        ) : !info ? (
          <p className="text-gray-600">Não foi possível carregar seus dados de indicação.</p>
        ) : (
          <>
            <div className="bg-white rounded-lg shadow p-6 space-y-3">
              <p className="text-gray-700">
                Cada amigo que se cadastrar com seu link e confirmar o e-mail te dá{' '}
                <strong>+1 app extra</strong> no seu plano, pra sempre.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={info.referral_link}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                />
                <button
                  type="button"
                  onClick={copyLink}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition shrink-0"
                >
                  {copied ? 'Copiado!' : 'Copiar'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-3xl font-bold text-indigo-600">{info.referred_count}</p>
                <p className="text-sm text-gray-600">Indicados</p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-3xl font-bold text-indigo-600">{info.activated_count}</p>
                <p className="text-sm text-gray-600">Confirmaram o e-mail</p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-3xl font-bold text-indigo-600">{info.bonus_app_slots}</p>
                <p className="text-sm text-gray-600">App(s) extra ganhos</p>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="font-semibold text-gray-900 mb-4">Seus indicados</h2>
              {info.referred.length === 0 ? (
                <p className="text-sm text-gray-500">Ninguém se cadastrou com seu link ainda.</p>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {info.referred.map((r, i) => (
                    <li key={i} className="py-3 flex items-center justify-between">
                      <span className="text-gray-800">{r.full_name}</span>
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                        r.is_verified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {r.is_verified ? 'Confirmado' : 'Aguardando confirmação'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
