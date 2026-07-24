'use client'

import Link from 'next/link'
import { useAuthStore } from '@/store/useAuthStore'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { authService } from '@/lib/auth'

export default function Home() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    authService.loadTokenFromStorage().finally(() => setChecking(false))
  }, [])

  useEffect(() => {
    if (!checking && isAuthenticated) {
      router.push('/dashboard')
    }
  }, [checking, isAuthenticated, router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="text-2xl font-bold text-indigo-600">Plataforma de Apps</div>
          <div className="space-x-4">
            <Link href="/auth/login" className="text-gray-600 hover:text-gray-900">
              Login
            </Link>
            <Link
              href="/auth/register"
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
            >
              Registrar
            </Link>
          </div>
        </div>
      </nav>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6">
            Crie Aplicativos Sem Programação
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Transforme sua ideia em um aplicativo profissional em minutos. Sem código, sem complicação.
          </p>
          <Link
            href="/auth/register"
            className="inline-block bg-indigo-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-indigo-700 transition"
          >
            Comece Grátis
          </Link>
        </div>

        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              title: 'Sem Programação',
              description: 'Interface visual intuitiva, sem necessidade de código',
            },
            {
              title: 'Templates Prontos',
              description: 'Modelos profissionais para diferentes tipos de negócio',
            },
            {
              title: 'Publicação Automática',
              description: 'Publique nas lojas do Android e iOS automaticamente',
            },
          ].map((feature, idx) => (
            <div key={idx} className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {feature.title}
              </h3>
              <p className="text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
