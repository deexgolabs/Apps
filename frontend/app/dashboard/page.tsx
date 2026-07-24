'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useAppStore } from '@/store/useAppStore'
import api from '@/lib/api'
import toast from 'react-hot-toast'

export default function DashboardPage() {
  const apps = useAppStore((state) => state.apps)
  const setApps = useAppStore((state) => state.setApps)

  useEffect(() => {
    const fetchApps = async () => {
      try {
        const response = await api.get('/api/apps')
        setApps(response.data)
      } catch (error) {
        toast.error('Erro ao carregar apps')
      }
    }

    fetchApps()
  }, [setApps])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900">Meus Aplicativos</h2>
        <Link
          href="/dashboard/apps/new"
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition"
        >
          + Novo App
        </Link>
      </div>

      {apps.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-600 mb-4">Você ainda não tem nenhum aplicativo</p>
          <Link
            href="/dashboard/apps/new"
            className="text-indigo-600 hover:text-indigo-700 font-semibold"
          >
            Crie seu primeiro app →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {apps.map((app) => (
            <div key={app.id} className="bg-white rounded-lg shadow hover:shadow-lg transition p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {app.name}
              </h3>
              <p className="text-gray-600 text-sm mb-4">
                {app.description || 'Sem descrição'}
              </p>
              <div className="flex justify-between items-center">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  app.status === 'published'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {app.status}
                </span>
                <Link
                  href={`/dashboard/apps/${app.id}`}
                  className="text-indigo-600 hover:text-indigo-700"
                >
                  Editar →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
