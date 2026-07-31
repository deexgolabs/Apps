'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { authService } from '@/lib/auth'
import api from '@/lib/api'
import toast from 'react-hot-toast'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [checking, setChecking] = useState(true)
  const [resending, setResending] = useState(false)
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    authService.loadTokenFromStorage().finally(() => setChecking(false))
  }, [])

  useEffect(() => {
    if (checking) return
    if (!useAuthStore.getState().isAuthenticated) {
      router.push('/auth/login')
    }
  }, [checking, router])

  const resendVerification = async () => {
    setResending(true)
    try {
      await api.post('/api/auth/resend-verification')
      toast.success('E-mail de verificação reenviado')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao reenviar e-mail')
    } finally {
      setResending(false)
    }
  }

  if (checking || !user) return null

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="text-2xl font-bold text-indigo-600">
            Plataforma de Apps
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900 text-sm">
              Meus Apps
            </Link>
            <Link href="/dashboard/billing" className="text-gray-600 hover:text-gray-900 text-sm">
              Meu plano
            </Link>
            <Link href="/dashboard/referrals" className="text-gray-600 hover:text-gray-900 text-sm">
              Indicações
            </Link>
            {user.is_admin && (
              <Link href="/dashboard/admin" className="text-gray-600 hover:text-gray-900 text-sm">
                Admin
              </Link>
            )}
            <span className="text-gray-600">Olá, {user.full_name}</span>
            <button
              onClick={() => {
                authService.logout()
                window.location.href = '/'
              }}
              className="text-gray-600 hover:text-gray-900"
            >
              Sair
            </button>
          </div>
        </div>
      </nav>

      {!user.is_verified && (
        <div className="bg-yellow-50 border-b border-yellow-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between gap-4">
            <p className="text-sm text-yellow-800">Confirme seu e-mail para garantir acesso total à sua conta.</p>
            <button
              onClick={resendVerification}
              disabled={resending}
              className="text-sm font-semibold text-yellow-800 hover:text-yellow-900 disabled:opacity-50 shrink-0"
            >
              {resending ? 'Enviando...' : 'Reenviar e-mail'}
            </button>
          </div>
        </div>
      )}

      {children}
    </div>
  )
}
