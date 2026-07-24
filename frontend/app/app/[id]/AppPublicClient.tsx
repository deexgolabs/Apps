'use client'

import { useEffect, useState } from 'react'
import { publicApi } from '@/lib/api'
import AppRuntime from '@/components/AppRuntime'
import type { Module } from '@/types'

interface PublicApp {
  id: number
  name: string
  config: Record<string, any>
  modules: string[]
}

export default function AppPublicClient({ appId }: { appId: string }) {
  const [app, setApp] = useState<PublicApp | null>(null)
  const [modules, setModules] = useState<Module[]>([])
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [appRes, modulesRes] = await Promise.all([
          publicApi.get(`/api/apps/${appId}/public`),
          publicApi.get('/api/modules'),
        ])
        setApp(appRes.data)
        setModules(modulesRes.data)
      } catch (error) {
        setNotFound(true)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [appId])

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js', { scope: '/app/' }).catch(() => {})
    }
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
        Carregando...
      </div>
    )
  }

  if (notFound || !app) {
    return (
      <div className="min-h-screen flex items-center justify-center text-center px-4">
        <p className="text-gray-500 text-sm">
          Este aplicativo não existe ou ainda não foi publicado.
        </p>
      </div>
    )
  }

  const config = app.config || {}

  return (
    <div className="min-h-screen bg-gray-50 relative max-w-md mx-auto shadow-xl">
      <AppRuntime
        mode="public"
        appId={appId}
        appName={app.name}
        modules={modules}
        activeModules={app.modules || []}
        primaryColor={config.primary_color || '#4F46E5'}
        secondaryColor={config.secondary_color || '#10B981'}
        logoUrl={config.logo_url || ''}
        homeModule={config.home_module || ''}
        homeImageUrl={config.home_image_url || ''}
      />
    </div>
  )
}
