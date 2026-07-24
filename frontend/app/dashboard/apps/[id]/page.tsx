'use client'

import { use, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { useAppStore } from '@/store/useAppStore'
import { useAuthStore } from '@/store/useAuthStore'
import ModuleSettingsModal from '@/components/ModuleSettingsModal'
import AppPreview from '@/components/AppPreview'
import AddModulePanel from '@/components/AddModulePanel'
import UsagePanel from '@/components/UsagePanel'
import PublishPanel from '@/components/PublishPanel'
import OrdersList from '@/components/OrdersList'
import PushComposer from '@/components/PushComposer'
import PushHistory from '@/components/PushHistory'
import ImageUploadField from '@/components/ImageUploadField'
import type { App, Module } from '@/types'
import toast from 'react-hot-toast'

interface PageProps {
  params: Promise<{ id: string }>
}

const FONT_OPTIONS = [
  { value: '', label: 'Padrão do sistema' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: 'Verdana, sans-serif', label: 'Verdana' },
  { value: "'Courier New', monospace", label: 'Courier New' },
  { value: "'Trebuchet MS', sans-serif", label: 'Trebuchet MS' },
]

type Tab = 'geral' | 'marca' | 'modulos' | 'pedidos' | 'notificacoes' | 'publicar'

const BASE_TABS: { id: Tab; label: string }[] = [
  { id: 'geral', label: 'Geral' },
  { id: 'marca', label: 'Marca' },
  { id: 'modulos', label: 'Módulos' },
  { id: 'pedidos', label: 'Pedidos' },
  { id: 'publicar', label: 'Publicar' },
]

export default function AppEditorPage({ params }: PageProps) {
  const { id } = use(params)
  const router = useRouter()
  const updateAppInStore = useAppStore((state) => state.updateApp)
  const removeAppFromStore = useAppStore((state) => state.removeApp)
  const userPlan = useAuthStore((state) => state.user?.plan) || 'free'

  const [app, setApp] = useState<App | null>(null)
  const [modules, setModules] = useState<Module[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('geral')

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [primaryColor, setPrimaryColor] = useState('#4F46E5')
  const [secondaryColor, setSecondaryColor] = useState('#10B981')
  const [logoUrl, setLogoUrl] = useState('')
  const [iconUrl, setIconUrl] = useState('')
  const [splashUrl, setSplashUrl] = useState('')
  const [homeModule, setHomeModule] = useState('')
  const [homeImageUrl, setHomeImageUrl] = useState('')
  const [fontFamily, setFontFamily] = useState('')
  const [activeModules, setActiveModules] = useState<string[]>([])
  const [configuringModule, setConfiguringModule] = useState<string | null>(null)
  const [moduleConfigs, setModuleConfigs] = useState<Record<string, any>>({})
  const [configVersion, setConfigVersion] = useState(0)

  const fetchModuleConfigs = async () => {
    try {
      const response = await api.get(`/api/apps/${id}/module-configs`)
      setModuleConfigs(response.data)
    } catch (error) {
      // não bloqueia a tela por causa disso — só afeta ícone/nome exibido no builder
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [appRes, modulesRes] = await Promise.all([
          api.get(`/api/apps/${id}`),
          api.get('/api/modules'),
        ])

        const appData: App = appRes.data
        setApp(appData)
        setName(appData.name)
        setDescription(appData.description || '')
        setPrimaryColor(appData.config?.primary_color || '#4F46E5')
        setSecondaryColor(appData.config?.secondary_color || '#10B981')
        setLogoUrl(appData.config?.logo_url || '')
        setIconUrl(appData.config?.icon_url || '')
        setSplashUrl(appData.config?.splash_url || '')
        setHomeModule(appData.config?.home_module || '')
        setHomeImageUrl(appData.config?.home_image_url || '')
        setFontFamily(appData.config?.font_family || '')
        setActiveModules(appData.modules || [])
        setModules(modulesRes.data)
      } catch (error) {
        toast.error('Erro ao carregar aplicativo')
        router.push('/dashboard')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    fetchModuleConfigs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, router])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      const response = await api.put(`/api/apps/${id}`, {
        name,
        description,
        config: {
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          logo_url: logoUrl,
          icon_url: iconUrl,
          splash_url: splashUrl,
          home_module: homeModule,
          home_image_url: homeImageUrl,
          font_family: fontFamily,
        },
        modules: activeModules,
      })

      setApp(response.data)
      updateAppInStore(response.data)
      toast.success('Aplicativo salvo com sucesso!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar aplicativo')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Tem certeza que deseja excluir este aplicativo?')) return

    try {
      await api.delete(`/api/apps/${id}`)
      removeAppFromStore(Number(id))
      toast.success('Aplicativo excluído')
      router.push('/dashboard')
    } catch (error) {
      toast.error('Erro ao excluir aplicativo')
    }
  }

  const TABS: { id: Tab; label: string }[] = activeModules.includes('push_notifications')
    ? [...BASE_TABS.slice(0, 4), { id: 'notificacoes', label: 'Notificações' }, ...BASE_TABS.slice(4)]
    : BASE_TABS

  const checklistItems = [
    { label: 'Definir logo ou ícone do app', done: !!(logoUrl || iconUrl) },
    { label: 'Personalizar pelo menos um módulo (nome ou ícone)', done: Object.values(moduleConfigs).some((c: any) => c?.display_name || c?.icon || c?.icon_name) },
    { label: 'Publicar o aplicativo', done: app?.status === 'published' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-gray-600">Carregando...</p>
      </div>
    )
  }

  if (!app) return null

  return (
    <div className="py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Editar Aplicativo</h1>
          <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-700">
            ← Voltar
          </Link>
        </div>

        <div className="lg:grid lg:grid-cols-[1fr_320px] gap-8 items-start">
        <div className="bg-white rounded-lg shadow p-8">
          <div className="flex gap-2 border-b border-gray-200 mb-8">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                  activeTab === tab.id
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSave} className="space-y-8">
            {activeTab === 'geral' && (
              <div className="space-y-6">
                <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
                  <p className="text-sm font-medium text-indigo-900 mb-2">
                    Progresso: {checklistItems.filter((i) => i.done).length} de {checklistItems.length} concluído
                  </p>
                  <ul className="space-y-1">
                    {checklistItems.map((item) => (
                      <li key={item.label} className={`text-sm flex items-center gap-2 ${item.done ? 'text-indigo-700' : 'text-indigo-400'}`}>
                        <span>{item.done ? '✓' : '○'}</span>
                        {item.label}
                      </li>
                    ))}
                  </ul>
                </div>

                <UsagePanel appId={id} />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nome do Aplicativo
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Descrição
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 h-24"
                  />
                </div>
              </div>
            )}

            {activeTab === 'marca' && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Cor Primária
                    </label>
                    <input
                      type="color"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-full h-10 border border-gray-300 rounded-lg cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Cor Secundária
                    </label>
                    <input
                      type="color"
                      value={secondaryColor}
                      onChange={(e) => setSecondaryColor(e.target.value)}
                      className="w-full h-10 border border-gray-300 rounded-lg cursor-pointer"
                    />
                  </div>
                </div>

                <ImageUploadField label="Logo" value={logoUrl} onChange={setLogoUrl} />

                <ImageUploadField label="Ícone do app" value={iconUrl} onChange={setIconUrl} hint="Recomendado: 1024×1024px" />

                <ImageUploadField label="Imagem de abertura (splash)" value={splashUrl} onChange={setSplashUrl} hint="Recomendado: 2732×2732px" />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tela inicial
                  </label>
                  <select
                    value={homeModule}
                    onChange={(e) => setHomeModule(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  >
                    <option value="">Primeiro módulo ativo</option>
                    {activeModules.map((name) => (
                      <option key={name} value={name}>
                        {moduleConfigs[name]?.display_name || modules.find((m) => m.name === name)?.description || name}
                      </option>
                    ))}
                  </select>
                </div>

                <ImageUploadField
                  label="Imagem de destaque da tela inicial (opcional)"
                  value={homeImageUrl}
                  onChange={setHomeImageUrl}
                />
                <p className="text-xs text-gray-400 -mt-4">
                  Aparece no topo da tela inicial, com o conteúdo do módulo logo abaixo.
                </p>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Fonte</label>
                  <select
                    value={fontFamily}
                    onChange={(e) => setFontFamily(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  >
                    {FONT_OPTIONS.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {activeTab === 'modulos' && (
              <AddModulePanel
                modules={modules}
                activeModules={activeModules}
                userPlan={userPlan}
                primaryColor={primaryColor}
                onAdd={(name) => setActiveModules([...activeModules, name])}
              />
            )}

            {activeTab === 'pedidos' && (
              <OrdersList appId={id} />
            )}

            {activeTab === 'notificacoes' && (
              <div className="space-y-6">
                <PushComposer appId={id} />
                <hr className="border-gray-200" />
                <PushHistory appId={id} />
              </div>
            )}

            {activeTab === 'publicar' && (
              <PublishPanel app={app} onUpdated={setApp} />
            )}

            <div className="flex gap-4 pt-4 border-t border-gray-200">
              <button
                type="submit"
                disabled={saving}
                className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
              >
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="flex-1 border border-red-300 text-red-600 py-2 rounded-lg font-semibold hover:bg-red-50 transition"
              >
                Excluir Aplicativo
              </button>
            </div>
          </form>
        </div>

        <div className="mt-8 lg:mt-0 lg:sticky lg:top-8">
          <AppPreview
            appId={id}
            appName={name}
            modules={modules}
            activeModules={activeModules}
            primaryColor={primaryColor}
            secondaryColor={secondaryColor}
            logoUrl={logoUrl}
            homeModule={homeModule}
            homeImageUrl={homeImageUrl}
            fontFamily={fontFamily}
            editable
            onModulesChange={setActiveModules}
            onConfigureModule={setConfiguringModule}
            configVersion={configVersion}
          />
        </div>
        </div>
      </div>

      {configuringModule && (
        <ModuleSettingsModal
          appId={id}
          moduleName={configuringModule}
          moduleLabel={modules.find((m) => m.name === configuringModule)?.description || configuringModule}
          onClose={() => {
            setConfiguringModule(null)
            fetchModuleConfigs()
            setConfigVersion((v) => v + 1)
          }}
        />
      )}
    </div>
  )
}
