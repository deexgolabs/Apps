'use client'

import { use, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { useAppStore } from '@/store/useAppStore'
import { useAuthStore } from '@/store/useAuthStore'
import ModuleSettingsModal from '@/components/ModuleSettingsModal'
import AppPreview from '@/components/AppPreview'
import type { NavigationStyle, HomeScreenStyle } from '@/components/AppRuntime'
import AddModulePanel from '@/components/AddModulePanel'
import UsagePanel from '@/components/UsagePanel'
import PublishPanel from '@/components/PublishPanel'
import CustomDomainPanel from '@/components/CustomDomainPanel'
import VersionHistoryPanel from '@/components/VersionHistoryPanel'
import GuidedTour from '@/components/GuidedTour'
import ImportFromUrlPanel from '@/components/ImportFromUrlPanel'
import OrdersList from '@/components/OrdersList'
import CouponsManager from '@/components/CouponsManager'
import WebhooksManager from '@/components/WebhooksManager'
import SalesReport from '@/components/SalesReport'
import OpenTablesPanel from '@/components/OpenTablesPanel'
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

type Tab = 'geral' | 'marca' | 'modulos' | 'pedidos' | 'relatorios' | 'notificacoes' | 'publicar'

const TOUR_STEPS = [
  {
    selector: '[data-tour="tabs"]',
    title: 'Bem-vindo ao construtor!',
    text: 'Aqui você navega entre as configurações do seu app: informações gerais, marca, módulos, pedidos e publicação.',
  },
  {
    selector: '[data-tour="preview"]',
    title: 'Prévia em tempo real',
    text: 'Toda alteração aparece aqui na hora, do jeitinho que o cliente vai ver no celular dele.',
  },
  {
    selector: '[data-tour="modules-panel"]',
    title: 'Adicione módulos',
    text: 'Módulos são as funcionalidades do seu app: cardápio, catálogo, formulário de contato e muito mais. Adicione quantos quiser (respeitando o limite do seu plano).',
  },
  {
    selector: '[data-tour="save-button"]',
    title: 'Não esqueça de salvar',
    text: 'Toda alteração feita aqui só vale depois de clicar em Salvar.',
  },
  {
    selector: '[data-tour="publish-tab"]',
    title: 'Publique quando estiver pronto',
    text: 'Quando o app estiver do jeito que você quer, publique aqui pra ele ficar acessível pros seus clientes.',
  },
]

const BASE_TABS: { id: Tab; label: string }[] = [
  { id: 'geral', label: 'Geral' },
  { id: 'marca', label: 'Marca' },
  { id: 'modulos', label: 'Módulos' },
  { id: 'pedidos', label: 'Pedidos' },
  { id: 'relatorios', label: 'Relatórios' },
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
  const [clientName, setClientName] = useState('')
  const [clientEmail, setClientEmail] = useState('')
  const [primaryColor, setPrimaryColor] = useState('#4F46E5')
  const [secondaryColor, setSecondaryColor] = useState('#10B981')
  const [logoUrl, setLogoUrl] = useState('')
  const [iconUrl, setIconUrl] = useState('')
  const [splashUrl, setSplashUrl] = useState('')
  const [homeModule, setHomeModule] = useState('')
  const [homeImageUrl, setHomeImageUrl] = useState('')
  const [fontFamily, setFontFamily] = useState('')
  const [customCss, setCustomCss] = useState('')
  const [navigationStyle, setNavigationStyle] = useState<NavigationStyle>('hamburger')
  const [homeScreenStyle, setHomeScreenStyle] = useState<HomeScreenStyle>('content')
  const [activeModules, setActiveModulesRaw] = useState<string[]>([])
  const [moduleHistory, setModuleHistory] = useState<string[][]>([])
  const [moduleFuture, setModuleFuture] = useState<string[][]>([])
  const [configuringModule, setConfiguringModule] = useState<string | null>(null)
  const [moduleConfigs, setModuleConfigs] = useState<Record<string, any>>({})
  const [configVersion, setConfigVersion] = useState(0)
  const [versionsRefreshKey, setVersionsRefreshKey] = useState(0)

  // Desfazer/refazer cobre só a lista de módulos (adicionar/remover/reordenar)
  // — é onde o erro mais comum e mais fácil de reverter acontece; configuração
  // de cor/fonte/logo (aba Marca) não entra no histórico por enquanto.
  //
  // Cada setter aqui é chamado uma única vez, com valor já calculado a partir
  // do estado atual (lido direto da closure, não de dentro de outro updater)
  // -- setState updaters precisam ser puros, e encadear um setState com efeito
  // colateral dentro do updater de outro quebra sob o double-invoke do React
  // Strict Mode (usado no modo dev do Next.js): o histórico duplicava e
  // desfazer/refazer ficava inconsistente depois da primeira ação.
  const setActiveModules = (updater: string[] | ((prev: string[]) => string[])) => {
    const next = typeof updater === 'function' ? updater(activeModules) : updater
    if (JSON.stringify(next) === JSON.stringify(activeModules)) return
    setModuleHistory((h) => [...h, activeModules])
    setModuleFuture([])
    setActiveModulesRaw(next)
  }

  const undoModules = () => {
    if (moduleHistory.length === 0) return
    const previous = moduleHistory[moduleHistory.length - 1]
    setModuleFuture((f) => [activeModules, ...f])
    setModuleHistory((h) => h.slice(0, -1))
    setActiveModulesRaw(previous)
  }

  const redoModules = () => {
    if (moduleFuture.length === 0) return
    const next = moduleFuture[0]
    setModuleHistory((h) => [...h, activeModules])
    setModuleFuture((f) => f.slice(1))
    setActiveModulesRaw(next)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const isTyping = target && ['INPUT', 'TEXTAREA'].includes(target.tagName)
      if (isTyping) return
      const isUndo = (e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z'
      const isRedo = (e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'z'
      if (isUndo) {
        e.preventDefault()
        undoModules()
      } else if (isRedo) {
        e.preventDefault()
        redoModules()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchModuleConfigs = async () => {
    try {
      const response = await api.get(`/api/apps/${id}/module-configs`)
      setModuleConfigs(response.data)
    } catch (error) {
      // não bloqueia a tela por causa disso — só afeta ícone/nome exibido no builder
    }
  }

  const applyAppData = (appData: App) => {
    setApp(appData)
    setName(appData.name)
    setDescription(appData.description || '')
    setClientName(appData.client_name || '')
    setClientEmail(appData.client_email || '')
    setPrimaryColor(appData.config?.primary_color || '#4F46E5')
    setSecondaryColor(appData.config?.secondary_color || '#10B981')
    setLogoUrl(appData.config?.logo_url || '')
    setIconUrl(appData.config?.icon_url || '')
    setSplashUrl(appData.config?.splash_url || '')
    setHomeModule(appData.config?.home_module || '')
    setHomeImageUrl(appData.config?.home_image_url || '')
    setFontFamily(appData.config?.font_family || '')
    setCustomCss(appData.config?.custom_css || '')
    setNavigationStyle(appData.config?.navigation_style || 'hamburger')
    setHomeScreenStyle(appData.config?.home_screen_style || 'content')
    setActiveModulesRaw(appData.modules || [])
    setModuleHistory([])
    setModuleFuture([])
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [appRes, modulesRes] = await Promise.all([
          api.get(`/api/apps/${id}`),
          api.get('/api/modules'),
        ])

        applyAppData(appRes.data)
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

  const handleRestored = (appData: App) => {
    applyAppData(appData)
    updateAppInStore(appData)
    fetchModuleConfigs()
    setConfigVersion((v) => v + 1)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      const response = await api.put(`/api/apps/${id}`, {
        name,
        description,
        client_name: clientName,
        client_email: clientEmail,
        config: {
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          logo_url: logoUrl,
          icon_url: iconUrl,
          splash_url: splashUrl,
          home_module: homeModule,
          home_image_url: homeImageUrl,
          font_family: fontFamily,
          custom_css: customCss,
          navigation_style: navigationStyle,
          home_screen_style: homeScreenStyle,
        },
        modules: activeModules,
      })

      setApp(response.data)
      updateAppInStore(response.data)
      setVersionsRefreshKey((v) => v + 1)
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
          <div className="flex gap-2 border-b border-gray-200 mb-8" data-tour="tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                data-tour={tab.id === 'publicar' ? 'publish-tab' : undefined}
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

                <ImportFromUrlPanel
                  appId={id}
                  onImported={(result) => {
                    if (result.name) setName(result.name)
                    if (result.description) setDescription(result.description)
                    if (result.image_url) setLogoUrl(result.image_url)
                  }}
                />

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

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Cliente (opcional)
                    </label>
                    <input
                      type="text"
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                      placeholder="Nome do cliente/agência"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      Pra organizar seus apps por cliente, se você gerencia mais de um.
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      E-mail do cliente (opcional)
                    </label>
                    <input
                      type="email"
                      value={clientEmail}
                      onChange={(e) => setClientEmail(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    />
                  </div>
                </div>

                <VersionHistoryPanel key={versionsRefreshKey} appId={id} onRestored={handleRestored} />
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

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Estilo de navegação</label>
                  <select
                    value={navigationStyle}
                    onChange={(e) => setNavigationStyle(e.target.value as NavigationStyle)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  >
                    <option value="hamburger">Menu hambúrguer (☰)</option>
                    <option value="bottom_tabs">Barra inferior de abas</option>
                  </select>
                  <p className="text-xs text-gray-400 mt-1">
                    Como o cliente vai navegar entre os módulos do app.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Tela inicial</label>
                  <select
                    value={homeScreenStyle}
                    onChange={(e) => setHomeScreenStyle(e.target.value as HomeScreenStyle)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  >
                    <option value="content">Conteúdo do módulo inicial</option>
                    <option value="icon_grid">Grade de ícones (estilo tela de apps)</option>
                  </select>
                  <p className="text-xs text-gray-400 mt-1">
                    Grade de ícones mostra todos os módulos como atalhos, tipo tela inicial de celular.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">CSS customizado (avançado)</label>
                  <textarea
                    value={customCss}
                    onChange={(e) => setCustomCss(e.target.value)}
                    spellCheck={false}
                    placeholder={'.app-header { border-radius: 0 0 16px 16px; }'}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 h-32 font-mono text-xs"
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Regras CSS aplicadas por cima do estilo padrão do app, tanto aqui na prévia quanto no app publicado. Use com cuidado — erros de sintaxe não travam o app, só não têm efeito.
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'modulos' && (
              <div className="space-y-3" data-tour="modules-panel">
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={undoModules}
                    disabled={moduleHistory.length === 0}
                    title="Desfazer (Ctrl+Z)"
                    className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:hover:bg-transparent"
                  >
                    ↩ Desfazer
                  </button>
                  <button
                    type="button"
                    onClick={redoModules}
                    disabled={moduleFuture.length === 0}
                    title="Refazer (Ctrl+Shift+Z)"
                    className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:hover:bg-transparent"
                  >
                    ↪ Refazer
                  </button>
                </div>
                <AddModulePanel
                  modules={modules}
                  activeModules={activeModules}
                  userPlan={userPlan}
                  primaryColor={primaryColor}
                  onAdd={(name) => setActiveModules([...activeModules, name])}
                />
              </div>
            )}

            {activeTab === 'pedidos' && (
              <div className="space-y-4">
                <CouponsManager appId={id} />
                <WebhooksManager appId={id} />
                <OpenTablesPanel appId={id} />
                <OrdersList appId={id} />
              </div>
            )}

            {activeTab === 'relatorios' && <SalesReport appId={id} />}

            {activeTab === 'notificacoes' && (
              <div className="space-y-6">
                <PushComposer appId={id} />
                <hr className="border-gray-200" />
                <PushHistory appId={id} />
              </div>
            )}

            {activeTab === 'publicar' && (
              <div className="space-y-6">
                <PublishPanel app={app} onUpdated={setApp} />
                <CustomDomainPanel appId={id} />
              </div>
            )}

            <div className="flex gap-4 pt-4 border-t border-gray-200" data-tour="save-button">
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

        <div className="mt-8 lg:mt-0 lg:sticky lg:top-8" data-tour="preview">
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
            customCss={customCss}
            navigationStyle={navigationStyle}
            homeScreenStyle={homeScreenStyle}
            editable
            onModulesChange={setActiveModules}
            onConfigureModule={setConfiguringModule}
            configVersion={configVersion}
          />
        </div>
        </div>
      </div>

      {!loading && app && (
        <GuidedTour
          storageKey="platform_tour_v1_seen"
          steps={TOUR_STEPS}
          onStepChange={(index) => {
            if (index === 2) setActiveTab('modulos')
          }}
        />
      )}

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
