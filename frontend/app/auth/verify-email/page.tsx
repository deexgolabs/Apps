'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { publicApi } from '@/lib/api'

function VerifyEmailStatus() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') || ''
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      return
    }

    publicApi
      .get('/api/auth/verify-email', { params: { token } })
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [token])

  if (status === 'loading') {
    return <p className="text-sm text-gray-500 text-center">Verificando...</p>
  }

  if (status === 'success') {
    return <p className="text-sm text-green-600 text-center">E-mail verificado com sucesso!</p>
  }

  return <p className="text-sm text-red-600 text-center">Link inválido ou expirado.</p>
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900">
          Verificação de e-mail
        </h1>
        <Suspense fallback={<p className="text-sm text-gray-500 text-center">Carregando...</p>}>
          <VerifyEmailStatus />
        </Suspense>
        <p className="mt-4 text-center text-sm text-gray-600">
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700 font-semibold">
            Ir para o painel
          </Link>
        </p>
      </div>
    </div>
  )
}
