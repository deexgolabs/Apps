'use client'

import { useState } from 'react'
import Link from 'next/link'
import { publicApi } from '@/lib/api'
import toast from 'react-hot-toast'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await publicApi.post('/api/auth/forgot-password', { email })
      setSent(true)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao solicitar redefinição')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900">
          Esqueci minha senha
        </h1>

        {sent ? (
          <p className="text-sm text-gray-600 text-center">
            Se o e-mail existir, um link de redefinição foi enviado. Confira sua caixa de entrada.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                placeholder="seu@email.com"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {loading ? 'Enviando...' : 'Enviar link de redefinição'}
            </button>
          </form>
        )}

        <p className="mt-4 text-center text-sm text-gray-600">
          <Link href="/auth/login" className="text-indigo-600 hover:text-indigo-700 font-semibold">
            Voltar para o login
          </Link>
        </p>
      </div>
    </div>
  )
}
