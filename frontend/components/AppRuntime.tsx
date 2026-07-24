'use client'

import { useEffect, useState } from 'react'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import api, { publicApi } from '@/lib/api'
import Skeleton from '@/components/Skeleton'
import {
  FIXED_FORM_MODULES,
  FORM_MODULE_FIELDS,
  LIST_MODULES,
  ORDER_MODULES,
  PAGAMENTO_ENTREGA_CUSTOMER_FIELDS,
  PAYMENT_GATEWAY_MODULES,
  parseCustomFields,
} from '@/lib/moduleFields'
import ModuleIcon from '@/components/ModuleIcon'
import type { Module, ModuleCategory, ModuleItem } from '@/types'
import toast from 'react-hot-toast'

export type RuntimeMode = 'owner' | 'public'

interface AppRuntimeProps {
  mode: RuntimeMode
  appId: string
  appName: string
  modules: Module[]
  activeModules: string[]
  primaryColor: string
  secondaryColor: string
  logoUrl: string
  homeModule: string
  homeImageUrl?: string
  fontFamily?: string
  editable?: boolean
  onModulesChange?: (names: string[]) => void
  onConfigureModule?: (name: string) => void
  configVersion?: number
}

function SortableModuleRow({
  name,
  label,
  config,
  primaryColor,
  selected,
  onSelect,
  onConfigure,
  onRemove,
}: {
  name: string
  label: string
  config: Record<string, any> | undefined
  primaryColor: string
  selected: boolean
  onSelect: () => void
  onConfigure: () => void
  onRemove: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: name })

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        backgroundColor: selected ? `${primaryColor}1A` : undefined,
      }}
      className="w-full flex items-center gap-2 pr-2 border-b border-gray-100"
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        className="text-gray-300 cursor-grab active:cursor-grabbing leading-none px-3 py-3"
        aria-label="Arrastar para reordenar"
      >
        ⠿
      </button>
      <button
        type="button"
        onClick={onSelect}
        className="flex-1 flex items-center gap-2 text-left truncate text-sm py-3 min-w-0"
        style={{ color: selected ? primaryColor : undefined, fontWeight: selected ? 600 : undefined }}
      >
        <ModuleIcon moduleName={name} config={config} color={primaryColor} size={14} />
        <span className="truncate">{label}</span>
      </button>
      <button
        type="button"
        onClick={onConfigure}
        className="text-gray-400 hover:text-indigo-600 text-sm leading-none px-1"
        aria-label={`Configurar ${name}`}
        title="Configurar"
      >
        ⚙
      </button>
      <button
        type="button"
        onClick={onRemove}
        className="text-gray-400 hover:text-red-600 text-sm leading-none px-1"
        aria-label={`Remover ${name}`}
      >
        ×
      </button>
    </div>
  )
}

function ModuleContent({ moduleName, settings }: { moduleName: string; settings: Record<string, any> | undefined }) {
  if (!settings || Object.keys(settings).length === 0) {
    return (
      <p className="text-sm text-gray-400 italic text-center mt-8">
        Este módulo ainda não foi configurado.
      </p>
    )
  }

  switch (moduleName) {
    case 'texto':
      return (
        <div>
          <h3 className="font-semibold text-gray-900 mb-2">{settings.titulo}</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{settings.conteudo}</p>
        </div>
      )
    case 'quem_somos':
      return (
        <div>
          {settings.imagem_url && (
            <img src={settings.imagem_url} alt="" className="w-full h-32 object-cover rounded-md mb-3" />
          )}
          <h3 className="font-semibold text-gray-900 mb-2">{settings.titulo}</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{settings.texto}</p>
        </div>
      )
    case 'video':
      return settings.url ? (
        <iframe src={settings.url} className="w-full h-40 rounded-md border-0" allowFullScreen />
      ) : null
    case 'pagina_web':
      return settings.url ? (
        <iframe src={settings.url} className="w-full h-64 rounded-md border-0" />
      ) : null
    case 'whatsapp':
      return (
        <div className="text-center space-y-3">
          {settings.mensagem_padrao && <p className="text-sm text-gray-600">{settings.mensagem_padrao}</p>}
          <a
            href={`https://wa.me/${settings.numero}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-green-500 text-white px-4 py-2 rounded-lg font-semibold hover:bg-green-600 transition"
          >
            Falar no WhatsApp
          </a>
        </div>
      )
    case 'mapa':
      return (
        <div>
          <p className="text-sm text-gray-700 mb-2">{settings.endereco}</p>
          <div className="w-full h-32 bg-gray-200 rounded-md flex items-center justify-center text-gray-400 text-xs">
            Mapa · {settings.latitude}, {settings.longitude}
          </div>
        </div>
      )
    case 'radio_web':
      return (
        <div>
          <p className="font-semibold text-gray-900 mb-2">{settings.nome_radio}</p>
          {settings.stream_url && <audio controls src={settings.stream_url} className="w-full" />}
        </div>
      )
    case 'rss':
      return <p className="text-sm text-gray-600">Conteúdo de {settings.feed_url}</p>
    case 'wordpress':
      return <p className="text-sm text-gray-600">Conteúdo de {settings.site_url}</p>
    case 'google_agenda':
      return settings.calendar_embed_url ? (
        <iframe src={settings.calendar_embed_url} className="w-full h-64 rounded-md border-0" />
      ) : null
    case 'slider_imagens':
      const imagens = (settings.imagens || '').split('\n').map((s: string) => s.trim()).filter(Boolean)
      return (
        <div className="flex gap-2 overflow-x-auto">
          {imagens.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Nenhuma imagem adicionada</p>
          ) : (
            imagens.map((url: string, idx: number) => (
              <img key={idx} src={url} alt="" className="w-24 h-24 object-cover rounded-md flex-shrink-0" />
            ))
          )}
        </div>
      )
    case 'chat_tawkto':
      return (
        <div className="relative h-40">
          <div className="absolute bottom-0 right-0 w-12 h-12 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xl shadow-lg">
            💬
          </div>
          <p className="text-sm text-gray-400 italic">Widget de chat (ID: {settings.widget_id})</p>
        </div>
      )
    case 'google_admob':
      return (
        <div className="w-full h-16 bg-gray-200 rounded-md flex items-center justify-center text-gray-400 text-xs">
          Anúncio · {settings.ad_unit_id}
        </div>
      )
    case 'cartao_fidelidade': {
      const total = parseInt(settings.total_selos, 10) || 0
      const preenchidos = Math.min(3, total)
      return (
        <div className="text-center space-y-3">
          <h3 className="font-semibold text-gray-900">{settings.titulo}</h3>
          {settings.regra && <p className="text-sm text-gray-600">{settings.regra}</p>}
          <div className="flex flex-wrap justify-center gap-1.5">
            {Array.from({ length: total }).map((_, idx) => (
              <div
                key={idx}
                className={`w-6 h-6 rounded-full border-2 ${
                  idx < preenchidos ? 'bg-indigo-600 border-indigo-600' : 'border-gray-300'
                }`}
              />
            ))}
          </div>
          {settings.premio && (
            <p className="text-sm text-gray-700">
              Prêmio: <span className="font-semibold">{settings.premio}</span>
            </p>
          )}
        </div>
      )
    }
    default:
      return null
  }
}

function ListModuleContent({
  mode,
  appId,
  moduleName,
  layout,
}: {
  mode: RuntimeMode
  appId: string
  moduleName: string
  layout: 'list' | 'grid'
}) {
  const [items, setItems] = useState<ModuleItem[]>([])
  const [categories, setCategories] = useState<ModuleCategory[]>([])
  const [loading, setLoading] = useState(true)
  const supportsCategories = LIST_MODULES[moduleName]

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const client = mode === 'owner' ? api : publicApi
        const base =
          mode === 'owner'
            ? `/api/apps/${appId}/modules/${moduleName}`
            : `/api/apps/${appId}/public/modules/${moduleName}`
        const itemsPromise = client.get<ModuleItem[]>(`${base}/items`)
        const categoriesPromise = supportsCategories
          ? client.get<ModuleCategory[]>(`${base}/categories`)
          : Promise.resolve(null)

        const [itemsRes, categoriesRes] = await Promise.all([itemsPromise, categoriesPromise])
        setItems(itemsRes.data)
        if (categoriesRes) setCategories(categoriesRes.data)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [mode, appId, moduleName, supportsCategories])

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    )
  }
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic text-center mt-8">
        Este módulo ainda não foi configurado.
      </p>
    )
  }

  const isAgenda = moduleName === 'agenda_interna'
  const isGrid = layout === 'grid'

  const renderItem = (item: ModuleItem) => (
    <div key={item.id} className="flex items-center gap-2 border-b border-gray-100 pb-2">
      {item.image_url && (
        <img src={item.image_url} alt="" className="w-10 h-10 object-cover rounded flex-shrink-0" />
      )}
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {item.name}
          {item.price != null && <span className="text-gray-500 font-normal"> · R$ {item.price.toFixed(2)}</span>}
          {isAgenda && (item.extra?.data || item.extra?.hora) && (
            <span className="text-gray-500 font-normal">
              {' '}
              · {item.extra?.data} {item.extra?.hora}
            </span>
          )}
        </p>
        {item.description && <p className="text-xs text-gray-500 truncate">{item.description}</p>}
      </div>
    </div>
  )

  // Grade de cards: colunas CSS (não grid-template) para o efeito "masonry" —
  // cada card mantém sua altura natural em vez de forçar linhas com altura igual.
  const renderCardItem = (item: ModuleItem) => (
    <div
      key={item.id}
      className="break-inside-avoid mb-2 bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm"
    >
      {item.image_url ? (
        <img src={item.image_url} alt="" className="w-full h-24 object-cover" />
      ) : (
        <div className="w-full h-16 bg-gray-100 flex items-center justify-center text-gray-300 text-xs">
          Sem imagem
        </div>
      )}
      <div className="p-2">
        <p className="text-xs font-medium text-gray-900 truncate">{item.name}</p>
        {item.price != null && <p className="text-xs text-gray-500">R$ {item.price.toFixed(2)}</p>}
        {isAgenda && (item.extra?.data || item.extra?.hora) && (
          <p className="text-[11px] text-gray-500">{item.extra?.data} {item.extra?.hora}</p>
        )}
        {item.description && <p className="text-[11px] text-gray-500 line-clamp-2">{item.description}</p>}
      </div>
    </div>
  )

  const itemsGrid = (list: ModuleItem[]) =>
    isGrid ? (
      <div className="columns-2 gap-2">{list.map(renderCardItem)}</div>
    ) : (
      <div className="space-y-2">{list.map(renderItem)}</div>
    )

  if (!supportsCategories) {
    return itemsGrid(items)
  }

  const uncategorized = items.filter((i) => !i.category_id)
  return (
    <div className="space-y-4">
      {categories.map((category) => {
        const categoryItems = items.filter((i) => i.category_id === category.id)
        if (categoryItems.length === 0) return null
        return (
          <div key={category.id}>
            {isGrid ? (
              <span className="inline-block bg-gray-100 border border-gray-200 rounded-lg px-3 py-1.5 mb-2 text-xs font-semibold text-gray-700 uppercase">
                {category.name}
              </span>
            ) : (
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{category.name}</p>
            )}
            {itemsGrid(categoryItems)}
          </div>
        )
      })}
      {uncategorized.length > 0 && itemsGrid(uncategorized)}
    </div>
  )
}

function FormModuleContent({ appId, moduleName }: { appId: string; moduleName: string }) {
  const fields = FORM_MODULE_FIELDS[moduleName] || []
  const [values, setValues] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  const isOrder = ORDER_MODULES.includes(moduleName)

  const handleSubmit = async () => {
    setSending(true)
    try {
      const endpoint = isOrder ? 'orders' : 'submissions'
      const headers = isOrder ? endUserAuthHeader(appId) : undefined
      await publicApi.post(`/api/apps/${appId}/modules/${moduleName}/${endpoint}`, { data: values }, { headers })
      setSent(true)
      setValues({})
    } catch (error) {
      toast.error('Erro ao enviar formulário')
    } finally {
      setSending(false)
    }
  }

  if (sent) {
    return (
      <div className="text-center mt-8">
        <p className="text-sm text-gray-700 font-medium">
          {isOrder ? 'Pedido enviado! Obrigado.' : 'Enviado! Obrigado.'}
        </p>
        <button
          type="button"
          onClick={() => setSent(false)}
          className="text-xs text-indigo-600 hover:text-indigo-700 mt-2"
        >
          Enviar outra resposta
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {fields.map((field) => (
        <div key={field.key}>
          {field.type === 'textarea' ? (
            <textarea
              value={values[field.key] || ''}
              onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
              placeholder={field.label}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          ) : (
            <input
              type={field.type === 'number' ? 'number' : field.type === 'url' ? 'url' : 'text'}
              value={values[field.key] || ''}
              onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
              placeholder={field.label}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          )}
        </div>
      ))}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={sending}
        className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {sending ? 'Enviando...' : 'Enviar'}
      </button>
    </div>
  )
}

function DynamicFormModuleContent({
  appId,
  moduleName,
  settings,
}: {
  appId: string
  moduleName: string
  settings: Record<string, any> | undefined
}) {
  const campos = parseCustomFields(settings?.campos || '')
  const [values, setValues] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  if (campos.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic text-center mt-8">
        Este módulo ainda não foi configurado.
      </p>
    )
  }

  const handleSubmit = async () => {
    setSending(true)
    try {
      await publicApi.post(`/api/apps/${appId}/modules/${moduleName}/submissions`, { data: values })
      setSent(true)
      setValues({})
    } catch (error) {
      toast.error('Erro ao enviar formulário')
    } finally {
      setSending(false)
    }
  }

  if (sent) {
    return (
      <div className="text-center mt-8">
        <p className="text-sm text-gray-700 font-medium">Enviado! Obrigado.</p>
        <button
          type="button"
          onClick={() => setSent(false)}
          className="text-xs text-indigo-600 hover:text-indigo-700 mt-2"
        >
          Enviar outra resposta
        </button>
      </div>
    )
  }

  const missingRequired = campos.some((field) => field.required && !values[field.key]?.trim())

  return (
    <div className="space-y-2">
      {campos.map((field) => (
        <input
          key={field.key}
          type={field.type === 'numero' ? 'number' : field.type === 'data' ? 'date' : 'text'}
          value={values[field.key] || ''}
          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
          placeholder={field.label + (field.required ? ' *' : '')}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
        />
      ))}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={sending || missingRequired}
        className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {sending ? 'Enviando...' : 'Enviar'}
      </button>
    </div>
  )
}

function FreteCalculator({ settings }: { settings: Record<string, any> | undefined }) {
  const [cep, setCep] = useState('')

  const rules: { prefix: string; price: number }[] = (settings?.regras || '')
    .split('\n')
    .map((line: string) => line.trim())
    .filter(Boolean)
    .map((line: string) => {
      const [prefix, price] = line.split(':')
      return { prefix: (prefix || '').trim(), price: parseFloat(price) }
    })
    .filter((r: { prefix: string; price: number }) => r.prefix && !isNaN(r.price))

  if (rules.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic text-center mt-8">
        Este módulo ainda não foi configurado.
      </p>
    )
  }

  const match = cep ? rules.find((r) => cep.startsWith(r.prefix)) : undefined

  return (
    <div className="space-y-3">
      <input
        type="text"
        value={cep}
        onChange={(e) => setCep(e.target.value)}
        placeholder="Digite seu CEP"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      {cep && (
        <p className="text-sm text-gray-700">
          {match ? (
            <>Frete: <span className="font-semibold">R$ {match.price.toFixed(2)}</span></>
          ) : (
            'Frete não disponível para esse CEP'
          )}
        </p>
      )}
    </div>
  )
}

function endUserSessionKey(appId: string) {
  return `end_user_session_${appId}`
}

// Se o cliente final estiver logado (login_cadastro), anexa o token na criação
// do pedido pra ele aparecer em "Meus pedidos" — opcional, formulário funciona
// igual pra visitante sem conta.
function endUserAuthHeader(appId: string): Record<string, string> {
  const saved = localStorage.getItem(endUserSessionKey(appId))
  if (!saved) return {}
  try {
    const { token } = JSON.parse(saved)
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}

const ORDER_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  confirmed: 'Confirmado',
  preparing: 'Preparando',
  completed: 'Concluído',
  cancelled: 'Cancelado',
}

function MyOrders({ appId, token }: { appId: string; token: string }) {
  const [orders, setOrders] = useState<{ id: number; module_name: string; status: string; created_at: string }[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    publicApi
      .get(`/api/apps/${appId}/my-orders`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => setOrders(response.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [appId, token])

  if (loading) return <p className="text-xs text-gray-400">Carregando pedidos...</p>

  if (orders.length === 0) return null

  return (
    <div className="text-left space-y-2 pt-2 border-t border-gray-200">
      <p className="text-sm font-medium text-gray-700">Meus pedidos</p>
      {orders.map((order) => (
        <div key={order.id} className="border border-gray-200 rounded-lg p-2 text-xs flex items-center justify-between">
          <span className="text-gray-600">
            {order.module_name} — {new Date(order.created_at).toLocaleDateString('pt-BR')}
          </span>
          <span className="font-medium text-gray-900">{ORDER_STATUS_LABELS[order.status] || order.status}</span>
        </div>
      ))}
    </div>
  )
}

function EndUserAuthWidget({ appId }: { appId: string }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [loggedInUser, setLoggedInUser] = useState<{ full_name: string } | null>(null)
  const [endUserToken, setEndUserToken] = useState<string | null>(null)

  // Restaura a sessão salva no localStorage, e trata o redirect de volta do
  // login via Facebook (?fb_token=... na URL) buscando os dados do usuário.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const fbToken = params.get('fb_token')

    if (fbToken) {
      publicApi
        .get(`/api/apps/${appId}/end-users/me`, {
          headers: { Authorization: `Bearer ${fbToken}` },
        })
        .then((response) => {
          localStorage.setItem(
            endUserSessionKey(appId),
            JSON.stringify({ token: fbToken, user: response.data })
          )
          setLoggedInUser(response.data)
          setEndUserToken(fbToken)
          toast.success('Login com Facebook realizado!')
          params.delete('fb_token')
          const newSearch = params.toString()
          window.history.replaceState({}, '', window.location.pathname + (newSearch ? `?${newSearch}` : ''))
        })
        .catch(() => toast.error('Erro ao concluir login com Facebook'))
      return
    }

    const saved = localStorage.getItem(endUserSessionKey(appId))
    if (saved) {
      try {
        const { user, token } = JSON.parse(saved)
        setLoggedInUser(user)
        setEndUserToken(token)
      } catch {
        localStorage.removeItem(endUserSessionKey(appId))
      }
    }
  }, [appId])

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const path = mode === 'register' ? 'register' : 'login'
      const payload =
        mode === 'register' ? { email, password, full_name: fullName } : { email, password }
      const response = await publicApi.post(`/api/apps/${appId}/end-users/${path}`, payload)
      localStorage.setItem(
        endUserSessionKey(appId),
        JSON.stringify({ token: response.data.access_token, user: response.data.user })
      )
      setLoggedInUser(response.data.user)
      setEndUserToken(response.data.access_token)
      toast.success(mode === 'register' ? 'Cadastro realizado!' : 'Login realizado!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao autenticar')
    } finally {
      setLoading(false)
    }
  }

  const handleFacebookLogin = async () => {
    try {
      const response = await publicApi.get(`/api/apps/${appId}/end-users/facebook/login-url`)
      window.location.href = response.data.url
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Login via Facebook não disponível')
    }
  }

  if (loggedInUser) {
    return (
      <div className="text-center space-y-3 mt-8">
        <p className="text-sm text-gray-700">Olá, <span className="font-semibold">{loggedInUser.full_name}</span>!</p>
        <button
          type="button"
          onClick={() => {
            localStorage.removeItem(endUserSessionKey(appId))
            setLoggedInUser(null)
            setEndUserToken(null)
            setEmail('')
            setPassword('')
            setFullName('')
          }}
          className="text-xs text-indigo-600 hover:text-indigo-700"
        >
          Sair
        </button>
        {endUserToken && <MyOrders appId={appId} token={endUserToken} />}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2 mb-2">
        <button
          type="button"
          onClick={() => setMode('login')}
          className={`flex-1 py-1 text-xs rounded-lg font-medium ${
            mode === 'login' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}
        >
          Entrar
        </button>
        <button
          type="button"
          onClick={() => setMode('register')}
          className={`flex-1 py-1 text-xs rounded-lg font-medium ${
            mode === 'register' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}
        >
          Cadastrar
        </button>
      </div>
      {mode === 'register' && (
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Nome"
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
        />
      )}
      <input
        type="text"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Senha"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={loading}
        className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {loading ? 'Aguarde...' : mode === 'register' ? 'Cadastrar' : 'Entrar'}
      </button>
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <div className="flex-1 h-px bg-gray-200" />
        ou
        <div className="flex-1 h-px bg-gray-200" />
      </div>
      <button
        type="button"
        onClick={handleFacebookLogin}
        className="w-full bg-[#1877F2] text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-[#1465d1] transition"
      >
        Continuar com Facebook
      </button>
    </div>
  )
}

const GATEWAY_LABELS: Record<string, string> = {
  mercado_pago: 'Mercado Pago',
  paypal: 'PayPal',
  pagseguro: 'PagSeguro',
}

function PaymentWidget({
  appId,
  moduleName,
  settings,
}: {
  appId: string
  moduleName: string
  settings: Record<string, any> | undefined
}) {
  const [loading, setLoading] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [customerValues, setCustomerValues] = useState<Record<string, string>>({})
  const [orderId, setOrderId] = useState<number | null>(null)
  const [orderStatus, setOrderStatus] = useState<string | null>(null)
  const isGateway = PAYMENT_GATEWAY_MODULES.includes(moduleName)

  if (!settings?.titulo) {
    return (
      <p className="text-sm text-gray-400 italic text-center mt-8">
        Este módulo ainda não foi configurado.
      </p>
    )
  }

  if (confirmed) {
    return (
      <div className="text-center mt-8">
        <p className="text-sm text-gray-700 font-medium">Pedido confirmado!</p>
        <button
          type="button"
          onClick={() => setConfirmed(false)}
          className="text-xs text-indigo-600 hover:text-indigo-700 mt-2"
        >
          Fazer outro pedido
        </button>
      </div>
    )
  }

  const handlePayEntrega = async () => {
    setLoading(true)
    try {
      await publicApi.post(
        `/api/apps/${appId}/modules/${moduleName}/orders`,
        { data: { titulo: settings.titulo, ...customerValues } },
        { headers: endUserAuthHeader(appId) }
      )
      setConfirmed(true)
      setCustomerValues({})
    } catch (error) {
      toast.error('Erro ao confirmar pedido')
    } finally {
      setLoading(false)
    }
  }

  const handleCheckout = async () => {
    setLoading(true)
    try {
      const response = await publicApi.post(`/api/apps/${appId}/modules/${moduleName}/checkout`)
      const url = response.data.checkout_url
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer')
        setOrderId(response.data.order_id)
        setOrderStatus('pending')
      } else {
        toast.error('A gateway não retornou um link de pagamento')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao iniciar pagamento')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmPayment = async () => {
    if (!orderId) return
    setLoading(true)
    try {
      const response = await publicApi.post(
        `/api/apps/${appId}/modules/${moduleName}/orders/${orderId}/confirm`
      )
      setOrderStatus(response.data.status)
      if (response.data.status === 'confirmed') {
        toast.success('Pagamento confirmado!')
      } else {
        toast.error('Ainda não identificamos o pagamento. Tente novamente após concluir no checkout.')
      }
    } catch (error) {
      toast.error('Erro ao confirmar pagamento')
    } finally {
      setLoading(false)
    }
  }

  if (isGateway && orderId) {
    return (
      <div className="text-center space-y-3">
        <h3 className="font-semibold text-gray-900">{settings.titulo}</h3>
        {orderStatus === 'confirmed' ? (
          <p className="text-sm text-gray-700 font-medium">Pagamento confirmado!</p>
        ) : (
          <>
            <p className="text-sm text-gray-600">Pedido criado — confirme depois de pagar no checkout.</p>
            <button
              type="button"
              onClick={handleConfirmPayment}
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {loading ? 'Verificando...' : 'Já paguei, confirmar'}
            </button>
          </>
        )}
        <button
          type="button"
          onClick={() => {
            setOrderId(null)
            setOrderStatus(null)
          }}
          className="text-xs text-indigo-600 hover:text-indigo-700"
        >
          Fazer outro pedido
        </button>
      </div>
    )
  }

  return (
    <div className="text-center space-y-3">
      <h3 className="font-semibold text-gray-900">{settings.titulo}</h3>
      {isGateway && settings.valor && (
        <p className="text-lg font-semibold text-gray-900">R$ {parseFloat(settings.valor).toFixed(2)}</p>
      )}
      {!isGateway && settings.instrucoes && (
        <p className="text-sm text-gray-600">{settings.instrucoes}</p>
      )}
      {!isGateway && (
        <div className="space-y-2 text-left">
          {PAGAMENTO_ENTREGA_CUSTOMER_FIELDS.map((field) =>
            field.type === 'textarea' ? (
              <textarea
                key={field.key}
                value={customerValues[field.key] || ''}
                onChange={(e) => setCustomerValues({ ...customerValues, [field.key]: e.target.value })}
                placeholder={field.label}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            ) : (
              <input
                key={field.key}
                type="text"
                value={customerValues[field.key] || ''}
                onChange={(e) => setCustomerValues({ ...customerValues, [field.key]: e.target.value })}
                placeholder={field.label}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            )
          )}
        </div>
      )}
      <button
        type="button"
        onClick={isGateway ? handleCheckout : handlePayEntrega}
        disabled={
          loading || (!isGateway && PAGAMENTO_ENTREGA_CUSTOMER_FIELDS.some((f) => !customerValues[f.key]?.trim()))
        }
        className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {loading ? 'Aguarde...' : isGateway ? `Pagar com ${GATEWAY_LABELS[moduleName]}` : 'Confirmar Pedido'}
      </button>
    </div>
  )
}

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

function PushSubscribeWidget({ mode, appId }: { mode: RuntimeMode; appId: string }) {
  const [subscribed, setSubscribed] = useState(false)
  const [loading, setLoading] = useState(false)

  if (mode === 'owner') {
    return (
      <p className="text-sm text-gray-400 italic text-center mt-8">
        Disponível para os visitantes depois que o app for publicado.
      </p>
    )
  }

  const handleSubscribe = async () => {
    setLoading(true)
    try {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        toast.error('Este navegador não suporta notificações push')
        return
      }

      const permission = await Notification.requestPermission()
      if (permission !== 'granted') {
        toast.error('Permissão de notificação negada')
        return
      }

      const keyResponse = await publicApi.get(`/api/apps/${appId}/public/push/vapid-public-key`)
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(keyResponse.data.public_key),
      })

      const json = subscription.toJSON()
      await publicApi.post(`/api/apps/${appId}/public/push/subscribe`, {
        endpoint: json.endpoint,
        keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth },
      })

      setSubscribed(true)
      toast.success('Notificações ativadas!')
    } catch (error) {
      toast.error('Erro ao ativar notificações')
    } finally {
      setLoading(false)
    }
  }

  if (subscribed) {
    return <p className="text-sm text-gray-700 text-center mt-8">Notificações ativadas ✓</p>
  }

  return (
    <div className="text-center mt-8">
      <button
        type="button"
        onClick={handleSubscribe}
        disabled={loading}
        className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {loading ? 'Aguarde...' : 'Ativar notificações'}
      </button>
    </div>
  )
}

export default function AppRuntime({
  mode,
  appId,
  appName,
  modules,
  activeModules,
  primaryColor,
  secondaryColor,
  logoUrl,
  homeModule,
  homeImageUrl,
  fontFamily,
  editable = false,
  onModulesChange,
  onConfigureModule,
  configVersion,
}: AppRuntimeProps) {
  const [configs, setConfigs] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [selectedModule, setSelectedModule] = useState(homeModule || activeModules[0] || '')

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const response =
          mode === 'owner'
            ? await api.get(`/api/apps/${appId}/module-configs`)
            : await publicApi.get(`/api/apps/${appId}/public/module-configs`)
        setConfigs(response.data)
      } finally {
        setLoading(false)
      }
    }
    fetchConfigs()
  }, [mode, appId, configVersion])

  useEffect(() => {
    if (!activeModules.includes(selectedModule)) {
      setSelectedModule(homeModule || activeModules[0] || '')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeModules, homeModule])

  const moduleByName = new Map(modules.map((m) => [m.name, m]))
  const isHomeScreen = selectedModule === (homeModule || activeModules[0])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = activeModules.indexOf(String(active.id))
    const newIndex = activeModules.indexOf(String(over.id))
    if (oldIndex === -1 || newIndex === -1) return
    onModulesChange?.(arrayMove(activeModules, oldIndex, newIndex))
  }

  return (
    <div className="contents" style={{ fontFamily: fontFamily || undefined }}>
      <div className="h-10 flex items-center justify-between px-3" style={{ backgroundColor: primaryColor }}>
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          className="text-white text-lg leading-none"
          aria-label="Abrir menu"
        >
          ☰
        </button>
        {logoUrl ? (
          <img src={logoUrl} alt={appName} className="h-6 object-contain" />
        ) : (
          <span className="text-white text-sm font-semibold truncate">{appName}</span>
        )}
        <span className="w-4" />
      </div>

      {isHomeScreen && homeImageUrl && (
        <img src={homeImageUrl} alt="" className="w-full h-32 object-cover shrink-0" />
      )}

      <div className="min-h-[320px] p-4" style={{ borderTop: `2px solid ${secondaryColor}` }}>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : activeModules.length === 0 ? (
          <p className="text-sm text-gray-400 italic text-center mt-8">Nenhum módulo ativo ainda</p>
        ) : (
          <div key={selectedModule} className="module-fade-in">
            {selectedModule in LIST_MODULES ? (
              <ListModuleContent
                mode={mode}
                appId={appId}
                moduleName={selectedModule}
                layout={configs[selectedModule]?.layout === 'grid' ? 'grid' : 'list'}
              />
            ) : FIXED_FORM_MODULES.includes(selectedModule) ? (
              <FormModuleContent appId={appId} moduleName={selectedModule} />
            ) : selectedModule === 'contato_personalizado' ? (
              <DynamicFormModuleContent
                appId={appId}
                moduleName={selectedModule}
                settings={configs[selectedModule]}
              />
            ) : selectedModule === 'calculo_frete' ? (
              <FreteCalculator settings={configs[selectedModule]} />
            ) : selectedModule === 'login_cadastro' ? (
              <EndUserAuthWidget appId={appId} />
            ) : selectedModule === 'push_notifications' ? (
              <PushSubscribeWidget mode={mode} appId={appId} />
            ) : PAYMENT_GATEWAY_MODULES.includes(selectedModule) || selectedModule === 'pagamento_entrega' ? (
              <PaymentWidget
                appId={appId}
                moduleName={selectedModule}
                settings={configs[selectedModule]}
              />
            ) : (
              <ModuleContent moduleName={selectedModule} settings={configs[selectedModule]} />
            )}
          </div>
        )}
      </div>

      {menuOpen && (
        <div className="absolute inset-0 bg-white/95 flex flex-col">
          <div className="h-10 flex items-center px-3" style={{ backgroundColor: primaryColor }}>
            <button
              type="button"
              onClick={() => setMenuOpen(false)}
              className="text-white text-lg leading-none"
              aria-label="Fechar menu"
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {editable ? (
              <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
                <SortableContext items={activeModules} strategy={verticalListSortingStrategy}>
                  {activeModules.map((name) => {
                    const module = moduleByName.get(name)
                    return (
                      <SortableModuleRow
                        key={name}
                        name={name}
                        label={configs[name]?.display_name || module?.description || name}
                        config={configs[name]}
                        primaryColor={primaryColor}
                        selected={selectedModule === name}
                        onSelect={() => {
                          setSelectedModule(name)
                          setMenuOpen(false)
                        }}
                        onConfigure={() => onConfigureModule?.(name)}
                        onRemove={() => {
                          const label = configs[name]?.display_name || module?.description || name
                          if (window.confirm(`Remover "${label}" deste app? A configuração salva fica guardada e volta se você adicionar o módulo de novo.`)) {
                            onModulesChange?.(activeModules.filter((m) => m !== name))
                          }
                        }}
                      />
                    )
                  })}
                </SortableContext>
              </DndContext>
            ) : (
              activeModules.map((name) => {
                const module = moduleByName.get(name)
                const selected = selectedModule === name
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => {
                      setSelectedModule(name)
                      setMenuOpen(false)
                    }}
                    className="w-full flex items-center gap-2 text-left px-4 py-3 text-sm border-b border-gray-100 hover:bg-gray-50"
                    style={{
                      backgroundColor: selected ? `${primaryColor}1A` : undefined,
                      color: selected ? primaryColor : undefined,
                      fontWeight: selected ? 600 : undefined,
                    }}
                  >
                    <ModuleIcon moduleName={name} config={configs[name]} color={primaryColor} size={14} />
                    <span className="truncate">{configs[name]?.display_name || module?.description || name}</span>
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
