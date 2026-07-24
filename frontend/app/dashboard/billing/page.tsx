'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { useAuthStore } from '@/store/useAuthStore'
import toast from 'react-hot-toast'

const PLANS = [
  { id: 'free', name: 'Free', price: 0, apps: 1, modules: 5, items: 10, categories: 5 },
  { id: 'pro', name: 'Pro', price: 29.9, apps: 1, modules: 10, items: 100, categories: 50 },
  { id: 'business', name: 'Business', price: 79.9, apps: 1, modules: 100, items: 10000, categories: 150 },
]

const GATEWAYS = [
  { id: 'mercado_pago', label: 'Mercado Pago' },
  { id: 'paypal', label: 'PayPal' },
  { id: 'pagseguro', label: 'PagSeguro' },
]

function BillingReturnHandler({ onConfirmed }: { onConfirmed: (plan: string) => void }) {
  const searchParams = useSearchParams()

  useEffect(() => {
    const plan = searchParams.get('plan')
    const status = searchParams.get('status')
    if (plan && status === 'success') {
      api.post('/api/billing/confirm', { plan })
        .then(() => {
          toast.success(`Plano atualizado para ${plan}`)
          onConfirmed(plan)
        })
        .catch(() => toast.error('Erro ao confirmar upgrade'))
    }
  }, [searchParams, onConfirmed])

  return null
}

export default function BillingPage() {
  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)
  const [loadingGateway, setLoadingGateway] = useState<string | null>(null)

  const checkout = async (plan: string, gateway: string) => {
    setLoadingGateway(`${plan}-${gateway}`)
    try {
      const response = await api.post('/api/billing/checkout', { gateway, plan })
      window.location.href = response.data.checkout_url
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao iniciar checkout')
    } finally {
      setLoadingGateway(null)
    }
  }

  const handleConfirmed = (plan: string) => {
    if (user) setUser({ ...user, plan: plan as any })
  }

  return (
    <div className="py-12 px-4">
      <Suspense fallback={null}>
        <BillingReturnHandler onConfirmed={handleConfirmed} />
      </Suspense>

      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Meu plano</h1>
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700">
            ← Voltar
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLANS.map((plan) => {
            const isCurrent = user?.plan === plan.id
            return (
              <div
                key={plan.id}
                className={`bg-white rounded-lg shadow p-6 border-2 ${isCurrent ? 'border-indigo-600' : 'border-transparent'}`}
              >
                <h2 className="text-xl font-bold text-gray-900">{plan.name}</h2>
                <p className="text-2xl font-bold text-indigo-600 my-2">
                  {plan.price === 0 ? 'Grátis' : `R$ ${plan.price.toFixed(2)}/mês`}
                </p>
                <ul className="text-sm text-gray-600 space-y-1 mb-6">
                  <li>{plan.apps} app(s)</li>
                  <li>{plan.modules} módulos</li>
                  <li>{plan.items} itens</li>
                  <li>{plan.categories} categorias</li>
                </ul>

                {isCurrent ? (
                  <span className="block text-center text-sm font-semibold text-indigo-600">Plano atual</span>
                ) : plan.id === 'free' ? (
                  <span className="block text-center text-sm text-gray-400">—</span>
                ) : (
                  <div className="space-y-2">
                    {GATEWAYS.map((gw) => (
                      <button
                        key={gw.id}
                        type="button"
                        onClick={() => checkout(plan.id, gw.id)}
                        disabled={loadingGateway === `${plan.id}-${gw.id}`}
                        className="w-full text-sm border border-gray-300 rounded-lg py-2 hover:bg-gray-50 disabled:opacity-50 transition"
                      >
                        {loadingGateway === `${plan.id}-${gw.id}` ? 'Aguarde...' : `Assinar via ${gw.label}`}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
