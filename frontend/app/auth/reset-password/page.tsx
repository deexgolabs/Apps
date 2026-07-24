'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { publicApi } from '@/lib/api'
import toast from 'react-hot-toast'

function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') || ''

  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await publicApi.post('/api/auth/reset-password', { token, new_password: newPassword })
      toast.success('Senha atualizada com sucesso!')
      router.push('/auth/login')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Link inválido ou expirado')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <p className="text-sm text-gray-600 text-center">
        Link inválido.{' '}
        <Link href="/auth/forgot-password" className="text-indigo-600 hover:text-indigo-700 font-semibold">
          Solicitar novo link
        </Link>
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nova senha</label>
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          minLength={6}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
          placeholder="••••••••"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {loading ? 'Salvando...' : 'Redefinir senha'}
      </button>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900">
          Redefinir senha
        </h1>
        <Suspense fallback={<p className="text-sm text-gray-500 text-center">Carregando...</p>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  )
}
