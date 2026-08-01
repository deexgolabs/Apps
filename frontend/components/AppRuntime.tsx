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
  CART_ENABLED_MODULES,
  FIXED_FORM_MODULES,
  FORM_MODULE_FIELDS,
  LIST_MODULES,
  ORDER_MODULES,
  PAGAMENTO_ENTREGA_CUSTOMER_FIELDS,
  PAYMENT_GATEWAY_MODULES,
  parseCustomFields,
} from '@/lib/moduleFields'
import ModuleIcon from '@/components/ModuleIcon'
import type { ItemVariation, Module, ModuleCategory, ModuleItem, Order } from '@/types'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'
import { endUserAuthHeader, endUserSessionKey } from '@/lib/endUserAuth'
import { CartProvider, useOptionalCart } from '@/context/CartContext'
import CartButton from '@/components/CartButton'
import CartDrawer from '@/components/CartDrawer'
import VariationPicker from '@/components/VariationPicker'
import ItemReviews from '@/components/ItemReviews'
import { parseFreteRules } from '@/lib/frete'
import OperatingHoursBadge from '@/components/OperatingHoursBadge'
import LoyaltyBalance from '@/components/LoyaltyBalance'
import WishlistButton from '@/components/WishlistButton'
import WishlistPanel from '@/components/WishlistPanel'
import InstallPwaButton from '@/components/InstallPwaButton'
import IconGridHomeScreen from '@/components/IconGridHomeScreen'
import BottomTabBar from '@/components/BottomTabBar'

export type RuntimeMode = 'owner' | 'public'

export type NavigationStyle = 'hamburger' | 'bottom_tabs'
export type HomeScreenStyle = 'content' | 'icon_grid'

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
  customCss?: string
  navigationStyle?: NavigationStyle
  homeScreenStyle?: HomeScreenStyle
  editable?: boolean
  onModulesChange?: (names: string[]) => void
  onConfigureModule?: (name: string) => void
  configVersion?: number
}

// CSS não executa script, mas um <style> ainda é HTML inserido via
// dangerouslySetInnerHTML -- corta qualquer tentativa de fechar a tag e injetar
// outra coisa (</style>, <script) antes de renderizar o CSS customizado do dono.
export function sanitizeCustomCss(css: string): string {
  return css.replace(/<\/style/gi, '').replace(/<script/gi, '')
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
    default:
      return null
  }
}

function ListModuleContent({
  mode,
  appId,
  moduleName,
  layout,
  cartEnabled,
  horarioFuncionamento,
  availableGateways,
}: {
  mode: RuntimeMode
  appId: string
  moduleName: string
  layout: 'list' | 'grid'
  cartEnabled?: boolean
  horarioFuncionamento?: string
  availableGateways?: string[]
}) {
  const cart = useOptionalCart()
  const [items, setItems] = useState<ModuleItem[]>([])
  const [categories, setCategories] = useState<ModuleCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [selectedVariations, setSelectedVariations] = useState<Record<number, number[]>>({})
  const [wishlistIds, setWishlistIds] = useState<Set<number>>(new Set())
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [unlockedIds, setUnlockedIds] = useState<Set<number>>(new Set())
  const [unlockingId, setUnlockingId] = useState<number | null>(null)
  const [pendingUnlockOrder, setPendingUnlockOrder] = useState<{ itemId: number; orderId: number } | null>(null)
  const [hasEndUserSession, setHasEndUserSession] = useState(false)
  const supportsCategories = LIST_MODULES[moduleName]
  const searchEnabled = cartEnabled && mode === 'public'
  const isPaywall = moduleName === 'conteudo_pago'

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const client = mode === 'owner' ? api : publicApi
        const base =
          mode === 'owner'
            ? `/api/apps/${appId}/modules/${moduleName}`
            : `/api/apps/${appId}/public/modules/${moduleName}`
        const params = searchEnabled
          ? { q: search || undefined, category_id: categoryFilter ?? undefined }
          : undefined
        const itemsPromise = client.get<ModuleItem[]>(`${base}/items`, { params })
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
    const timeout = setTimeout(fetchData, searchEnabled ? 300 : 0)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, appId, moduleName, supportsCategories, search, categoryFilter])

  useEffect(() => {
    if (mode !== 'public' || (!cartEnabled && !isPaywall)) return
    const hasSession = !!localStorage.getItem(endUserSessionKey(appId))
    setHasEndUserSession(hasSession)
    if (!hasSession) return
    if (cartEnabled) {
      publicApi
        .get(`/api/apps/${appId}/wishlist/me`, { headers: endUserAuthHeader(appId) })
        .then((res) => setWishlistIds(new Set(res.data.map((w: { item_id: number }) => w.item_id))))
        .catch(() => {})
    }
    if (isPaywall) {
      publicApi
        .get(`/api/apps/${appId}/modules/${moduleName}/unlocked-items`, { headers: endUserAuthHeader(appId) })
        .then((res) => setUnlockedIds(new Set(res.data as number[])))
        .catch(() => {})
    }
  }, [mode, appId, cartEnabled, isPaywall, moduleName])

  const toggleWishlist = async (item: ModuleItem) => {
    if (!hasEndUserSession) {
      toast.error('Faça login para favoritar')
      return
    }
    const headers = endUserAuthHeader(appId)
    try {
      if (wishlistIds.has(item.id)) {
        await publicApi.delete(`/api/apps/${appId}/wishlist/${item.id}`, { headers })
        setWishlistIds((prev) => {
          const next = new Set(prev)
          next.delete(item.id)
          return next
        })
      } else {
        await publicApi.post(`/api/apps/${appId}/modules/${moduleName}/items/${item.id}/wishlist`, {}, { headers })
        setWishlistIds((prev) => new Set(prev).add(item.id))
      }
    } catch (error) {
      showApiError(error, 'Não foi possível atualizar seus favoritos')
    }
  }

  const handleUnlock = async (item: ModuleItem) => {
    if (!hasEndUserSession) {
      toast.error('Faça login para desbloquear este conteúdo')
      return
    }
    if (!availableGateways || availableGateways.length === 0) {
      toast.error('O dono do app ainda não configurou um meio de pagamento para vender conteúdo pago.')
      return
    }
    setUnlockingId(item.id)
    try {
      const response = await publicApi.post(
        `/api/apps/${appId}/modules/${moduleName}/cart-checkout`,
        { items: [{ item_id: item.id, quantity: 1 }], gateway: availableGateways[0] },
        { headers: endUserAuthHeader(appId) }
      )
      const checkoutUrl = response.data.checkout_url
      if (checkoutUrl) {
        window.open(checkoutUrl, '_blank', 'noopener,noreferrer')
        setPendingUnlockOrder({ itemId: item.id, orderId: response.data.id })
      } else {
        toast.error('A gateway não retornou um link de pagamento')
      }
    } catch (error) {
      showApiError(error, 'Erro ao iniciar o desbloqueio')
    } finally {
      setUnlockingId(null)
    }
  }

  const handleConfirmUnlockPayment = async () => {
    if (!pendingUnlockOrder) return
    try {
      const response = await publicApi.post(
        `/api/apps/${appId}/orders/${pendingUnlockOrder.orderId}/confirm-payment`
      )
      if (response.data.status === 'confirmed') {
        toast.success('Conteúdo desbloqueado!')
        setUnlockedIds((prev) => new Set(prev).add(pendingUnlockOrder.itemId))
        setPendingUnlockOrder(null)
      } else {
        toast.error('Ainda não identificamos o pagamento. Conclua o pagamento e tente novamente.')
      }
    } catch (error) {
      showApiError(error, 'Erro ao confirmar pagamento')
    }
  }

  const isAgenda = moduleName === 'agenda_interna'
  const isBlog = moduleName === 'blog'
  const isEvent = moduleName === 'venda_ingressos'
  const isGrid = layout === 'grid'

  const formatBrDate = (iso?: string) => {
    if (!iso) return ''
    const [y, m, d] = iso.split('-')
    return d && m && y ? `${d}/${m}/${y}` : iso
  }

  // group_name null vira uma chave própria — trata todas as variações soltas
  // (fluxo antigo) como um único grupo que exige uma escolha, igual antes.
  const groupKeyOf = (v: ItemVariation) => v.group_name ?? '__none__'

  const selectedVariationObjs = (item: ModuleItem) =>
    (selectedVariations[item.id] || [])
      .map((id) => item.variations.find((v) => v.id === id))
      .filter((v): v is ItemVariation => !!v)

  const isCombo = (item: ModuleItem) => {
    const sel = selectedVariationObjs(item)
    return sel.length > 1 || sel.some((v) => v.group_name != null)
  }

  const outOfStock = (item: ModuleItem) => {
    if (item.variations.length > 0) {
      const sel = selectedVariationObjs(item)
      if (sel.length > 0) return sel.some((v) => v.stock !== null && v.stock <= 0)
      return item.variations.every((v) => v.stock !== null && v.stock <= 0)
    }
    return item.stock !== null && item.stock <= 0
  }

  const effectivePrice = (item: ModuleItem) => {
    if (item.variations.length > 0) {
      const sel = selectedVariationObjs(item)
      if (sel.length === 0) return item.variations[0]?.price ?? item.price
      if (isCombo(item)) return (item.price || 0) + sel.reduce((sum, v) => sum + v.price, 0)
      return sel[0].price
    }
    return item.extra?.promo_price ?? item.price
  }

  const handleSelectVariation = (item: ModuleItem, v: ItemVariation) => {
    setSelectedVariations((prev) => {
      const current = prev[item.id] || []
      const filtered = current.filter((id) => {
        const existing = item.variations.find((iv) => iv.id === id)
        return existing ? groupKeyOf(existing) !== groupKeyOf(v) : true
      })
      return { ...prev, [item.id]: [...filtered, v.id] }
    })
  }

  const addToCartButton = (item: ModuleItem) => {
    if (!cartEnabled || !cart) return null
    const sel = selectedVariationObjs(item)
    const requiredGroups = Array.from(new Set(item.variations.map(groupKeyOf)))
    const selectedGroups = new Set(sel.map(groupKeyOf))
    const needsVariation = item.variations.length > 0 && requiredGroups.some((g) => !selectedGroups.has(g))
    const trackedStocks = sel.filter((v) => v.stock !== null).map((v) => v.stock as number)
    const stockLimit = sel.length > 0 ? (trackedStocks.length > 0 ? Math.min(...trackedStocks) : null) : item.stock
    return (
      <button
        type="button"
        disabled={outOfStock(item) || needsVariation}
        onClick={() => {
          const name = sel.length > 0 ? `${item.name} (${sel.map((v) => v.name).join(', ')})` : item.name
          cart.addItem(moduleName, {
            id: item.id,
            variation_ids: sel.map((v) => v.id),
            name,
            price: effectivePrice(item),
            image_url: item.image_url,
            stock: stockLimit,
          })
        }}
        title={needsVariation ? 'Escolha uma opção em cada grupo' : undefined}
        className="shrink-0 text-xs font-semibold px-2 py-1 rounded bg-indigo-600 text-white disabled:opacity-40 disabled:bg-gray-400"
      >
        {outOfStock(item) ? 'Esgotado' : '+ Adicionar'}
      </button>
    )
  }

  const priceDisplay = (item: ModuleItem) => {
    const promo = item.extra?.promo_price
    if (item.variations.length > 0) {
      const hasGroups = item.variations.some((v) => v.group_name != null)
      let minPrice: number
      if (hasGroups) {
        // menor combo possível: preço base + a opção mais barata de cada grupo
        const groups = new Set(item.variations.map(groupKeyOf))
        minPrice = (item.price || 0) + Array.from(groups).reduce((sum, g) => {
          const cheapest = Math.min(...item.variations.filter((v) => groupKeyOf(v) === g).map((v) => v.price))
          return sum + cheapest
        }, 0)
      } else {
        minPrice = Math.min(...item.variations.map((v) => v.price))
      }
      return <span className="text-gray-500 font-normal"> · a partir de R$ {minPrice.toFixed(2)}</span>
    }
    if (promo != null && item.price != null) {
      return (
        <span className="font-normal">
          {' '}
          · <span className="line-through text-gray-400">R$ {item.price.toFixed(2)}</span>{' '}
          <span className="text-red-600 font-semibold">R$ {Number(promo).toFixed(2)}</span>
        </span>
      )
    }
    if (item.price != null) return <span className="text-gray-500 font-normal"> · R$ {item.price.toFixed(2)}</span>
    return null
  }

  const expandedPanel = (item: ModuleItem) =>
    expandedId === item.id && (
      <div className="px-2 pb-2 space-y-2" onClick={(e) => e.stopPropagation()}>
        {isBlog ? (
          <>
            {item.extra?.published_at && (
              <p className="text-[11px] text-gray-400">{formatBrDate(item.extra.published_at)}</p>
            )}
            {item.extra?.body && <p className="text-xs text-gray-700 whitespace-pre-line">{item.extra.body}</p>}
          </>
        ) : isPaywall ? (
          unlockedIds.has(item.id) ? (
            <>
              <p className="text-[11px] text-green-600 font-medium">🔓 Desbloqueado</p>
              {item.extra?.body && <p className="text-xs text-gray-700 whitespace-pre-line">{item.extra.body}</p>}
            </>
          ) : pendingUnlockOrder?.itemId === item.id ? (
            <div className="space-y-1.5">
              <p className="text-xs text-gray-600">
                Complete o pagamento na aba que abrimos e depois confirme aqui.
              </p>
              <button
                type="button"
                onClick={handleConfirmUnlockPayment}
                className="text-xs font-semibold px-2 py-1 rounded bg-indigo-600 text-white"
              >
                Já paguei
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => handleUnlock(item)}
              disabled={unlockingId === item.id}
              className="text-xs font-semibold px-3 py-1.5 rounded bg-indigo-600 text-white disabled:opacity-50"
            >
              {unlockingId === item.id ? 'Abrindo pagamento...' : `🔒 Desbloquear por R$ ${(item.price || 0).toFixed(2)}`}
            </button>
          )
        ) : (
          item.description && <p className="text-xs text-gray-500">{item.description}</p>
        )}
        {item.extra?.gallery?.length > 0 && (
          <div className="flex gap-1.5 overflow-x-auto">
            {item.extra.gallery.map((url: string, i: number) => (
              <img key={i} src={url} alt="" className="w-14 h-14 object-cover rounded flex-shrink-0" />
            ))}
          </div>
        )}
        {item.variations.length > 0 && (
          <VariationPicker
            variations={item.variations}
            selectedIds={selectedVariations[item.id] || []}
            onSelect={(v) => handleSelectVariation(item, v)}
          />
        )}
        {mode === 'public' && <ItemReviews appId={appId} moduleName={moduleName} itemId={item.id} />}
      </div>
    )

  const renderItem = (item: ModuleItem) => (
    <div key={item.id} className="border-b border-gray-100 pb-2">
      <div
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => mode === 'public' && setExpandedId(expandedId === item.id ? null : item.id)}
      >
        {item.image_url && (
          <img src={item.image_url} alt="" className="w-10 h-10 object-cover rounded flex-shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate">
            {item.extra?.featured && <span className="text-amber-500 mr-1">★</span>}
            {item.name}
            {priceDisplay(item)}
            {isAgenda && (item.extra?.data || item.extra?.hora) && (
              <span className="text-gray-500 font-normal">
                {' '}
                · {item.extra?.data} {item.extra?.hora}
              </span>
            )}
            {isBlog && item.extra?.published_at && (
              <span className="text-gray-400 font-normal"> · {formatBrDate(item.extra.published_at)}</span>
            )}
            {isEvent && (item.extra?.data || item.extra?.hora) && (
              <span className="text-gray-500 font-normal">
                {' '}
                · {formatBrDate(item.extra?.data)} {item.extra?.hora}
              </span>
            )}
            {isPaywall && (
              <span className="text-gray-400 font-normal"> · {unlockedIds.has(item.id) ? '🔓' : '🔒'}</span>
            )}
          </p>
          {isEvent && item.extra?.location && (
            <p className="text-xs text-gray-500 truncate">📍 {item.extra.location}</p>
          )}
          {isPaywall && item.description && (
            <p className="text-xs text-gray-500 line-clamp-2">{item.description}</p>
          )}
          {isBlog && item.description && (
            <p className="text-xs text-gray-500 line-clamp-2">{item.description}</p>
          )}
          {item.avg_rating != null && (
            <p className="text-[11px] text-amber-500">
              {'★'.repeat(Math.round(item.avg_rating))} ({item.review_count})
            </p>
          )}
        </div>
        {mode === 'public' && cartEnabled && (
          <WishlistButton favorited={wishlistIds.has(item.id)} onToggle={() => toggleWishlist(item)} />
        )}
        {addToCartButton(item)}
      </div>
      {expandedPanel(item)}
    </div>
  )

  // Grade de cards: colunas CSS (não grid-template) para o efeito "masonry" —
  // cada card mantém sua altura natural em vez de forçar linhas com altura igual.
  const renderCardItem = (item: ModuleItem) => (
    <div
      key={item.id}
      className="break-inside-avoid mb-2 bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm relative"
    >
      {item.extra?.featured && (
        <span className="absolute top-1 left-1 bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded">
          ★ Destaque
        </span>
      )}
      {mode === 'public' && cartEnabled && (
        <span className="absolute top-1 right-1 bg-white/90 rounded-full w-6 h-6 flex items-center justify-center shadow-sm">
          <WishlistButton favorited={wishlistIds.has(item.id)} onToggle={() => toggleWishlist(item)} />
        </span>
      )}
      <div
        className="cursor-pointer"
        onClick={() => mode === 'public' && setExpandedId(expandedId === item.id ? null : item.id)}
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
          <p className="text-xs">{priceDisplay(item)}</p>
          {isAgenda && (item.extra?.data || item.extra?.hora) && (
            <p className="text-[11px] text-gray-500">{item.extra?.data} {item.extra?.hora}</p>
          )}
          {isEvent && (item.extra?.data || item.extra?.hora) && (
            <p className="text-[11px] text-gray-500">{formatBrDate(item.extra?.data)} {item.extra?.hora}</p>
          )}
          {isEvent && item.extra?.location && (
            <p className="text-[11px] text-gray-500 truncate">📍 {item.extra.location}</p>
          )}
          {isBlog && item.extra?.published_at && (
            <p className="text-[11px] text-gray-400">{formatBrDate(item.extra.published_at)}</p>
          )}
          {isPaywall && (
            <p className="text-[11px] text-gray-400">{unlockedIds.has(item.id) ? '🔓 Desbloqueado' : '🔒 Bloqueado'}</p>
          )}
          {item.avg_rating != null && (
            <p className="text-[11px] text-amber-500">
              {'★'.repeat(Math.round(item.avg_rating))} ({item.review_count})
            </p>
          )}
          {item.description && <p className="text-[11px] text-gray-500 line-clamp-2">{item.description}</p>}
        </div>
      </div>
      <div className="px-2 pb-2">{cartEnabled && cart && addToCartButton(item)}</div>
      {expandedPanel(item)}
    </div>
  )

  const itemsGrid = (list: ModuleItem[]) =>
    isGrid ? (
      <div className="columns-2 gap-2">{list.map(renderCardItem)}</div>
    ) : (
      <div className="space-y-2">{list.map(renderItem)}</div>
    )

  const searchBar = searchEnabled && (
    <div className="mb-3">
      {horarioFuncionamento && <OperatingHoursBadge horarioFuncionamento={horarioFuncionamento} />}
      <div className="flex gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar..."
          className="flex-1 text-sm border border-gray-300 rounded px-2 py-1.5"
        />
        {supportsCategories && categories.length > 0 && (
          <select
            value={categoryFilter ?? ''}
            onChange={(e) => setCategoryFilter(e.target.value ? Number(e.target.value) : null)}
            className="text-sm border border-gray-300 rounded px-2 py-1.5"
          >
            <option value="">Todas categorias</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        {hasEndUserSession && (
          <WishlistPanel active={favoritesOnly} onToggle={() => setFavoritesOnly((v) => !v)} />
        )}
      </div>
    </div>
  )

  const filteredItems = favoritesOnly ? items.filter((i) => wishlistIds.has(i.id)) : items
  const displayItems = isBlog
    ? [...filteredItems].sort((a, b) => (b.extra?.published_at || '').localeCompare(a.extra?.published_at || ''))
    : isEvent
      ? [...filteredItems].sort((a, b) => (a.extra?.data || '').localeCompare(b.extra?.data || ''))
      : filteredItems

  if (loading) {
    return (
      <div>
        {searchBar}
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    )
  }

  if (displayItems.length === 0) {
    return (
      <div>
        {searchBar}
        <p className="text-sm text-gray-400 italic text-center mt-8">
          {favoritesOnly
            ? 'Nenhum item favoritado ainda.'
            : search || categoryFilter
              ? 'Nenhum item encontrado.'
              : 'Este módulo ainda não foi configurado.'}
        </p>
      </div>
    )
  }

  if (!supportsCategories) {
    return (
      <div>
        {searchBar}
        {itemsGrid(displayItems)}
      </div>
    )
  }

  const uncategorized = displayItems.filter((i) => !i.category_id)
  return (
    <div className="space-y-4">
      {searchBar}
      {categories.map((category) => {
        const categoryItems = displayItems.filter((i) => i.category_id === category.id)
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

function TableReservationWidget({
  appId,
  moduleName,
  settings,
}: {
  appId: string
  moduleName: string
  settings: Record<string, any> | undefined
}) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [partySize, setPartySize] = useState('2')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [notes, setNotes] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  const horarioFuncionamento = settings?.horario_funcionamento

  const missingRequired = !name.trim() || !phone.trim() || !date || !time || !partySize || Number(partySize) < 1

  const handleSubmit = async () => {
    setSending(true)
    try {
      const reservationAt = new Date(`${date}T${time}:00`).toISOString()
      await publicApi.post(
        `/api/apps/${appId}/modules/${moduleName}/reservations`,
        {
          customer_name: name,
          customer_phone: phone,
          party_size: Number(partySize),
          reservation_at: reservationAt,
          notes: notes.trim() || null,
        },
        { headers: endUserAuthHeader(appId) }
      )
      setSent(true)
      setName('')
      setPhone('')
      setPartySize('2')
      setDate('')
      setTime('')
      setNotes('')
    } catch (error: any) {
      showApiError(error, 'Erro ao reservar mesa')
    } finally {
      setSending(false)
    }
  }

  if (sent) {
    return (
      <div className="text-center mt-8">
        <p className="text-sm text-gray-700 font-medium">Reserva enviada! Aguarde a confirmação.</p>
        <button
          type="button"
          onClick={() => setSent(false)}
          className="text-xs text-indigo-600 hover:text-indigo-700 mt-2"
        >
          Fazer outra reserva
        </button>
      </div>
    )
  }

  const todayStr = new Date().toISOString().slice(0, 10)

  return (
    <div className="space-y-2">
      <OperatingHoursBadge horarioFuncionamento={horarioFuncionamento} />
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Nome"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      <input
        type="text"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        placeholder="Telefone"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      <div className="grid grid-cols-2 gap-2">
        <input
          type="date"
          value={date}
          min={todayStr}
          onChange={(e) => setDate(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
        />
        <input
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
        />
      </div>
      <input
        type="number"
        min={1}
        value={partySize}
        onChange={(e) => setPartySize(e.target.value)}
        placeholder="Número de pessoas"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Observações (opcional)"
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={sending || missingRequired}
        className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {sending ? 'Reservando...' : 'Reservar mesa'}
      </button>
    </div>
  )
}

function FreteCalculator({ settings }: { settings: Record<string, any> | undefined }) {
  const [cep, setCep] = useState('')

  const rules = parseFreteRules(settings?.regras || '')

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


const ORDER_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  confirmed: 'Confirmado',
  preparing: 'Preparando',
  completed: 'Concluído',
  cancelled: 'Cancelado',
}

const CANCELABLE_ORDER_STATUSES = new Set(['pending', 'confirmed'])

function MyOrders({ appId, token }: { appId: string; token: string }) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const cart = useOptionalCart()

  useEffect(() => {
    const fetchOrders = () => {
      publicApi
        .get(`/api/apps/${appId}/my-orders`, { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => setOrders(response.data))
        .catch(() => {})
        .finally(() => setLoading(false))
    }
    fetchOrders()
    const interval = setInterval(fetchOrders, 15000)
    return () => clearInterval(interval)
  }, [appId, token])

  const handleReorder = async (order: Order) => {
    if (!cart) return
    await cart.restoreFromOrder(order.items, order.module_name)
    toast.success('Itens do pedido adicionados ao carrinho!')
  }

  const handleCancel = async (order: Order) => {
    if (!window.confirm('Cancelar este pedido?')) return
    setCancellingId(order.id)
    try {
      const response = await publicApi.put(
        `/api/apps/${appId}/my-orders/${order.id}/cancel`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setOrders((prev) => prev.map((o) => (o.id === order.id ? response.data : o)))
      toast.success('Pedido cancelado')
    } catch (error) {
      showApiError(error, 'Não foi possível cancelar o pedido')
    } finally {
      setCancellingId(null)
    }
  }

  if (loading) return <p className="text-xs text-gray-400">Carregando pedidos...</p>

  if (orders.length === 0) return null

  return (
    <div className="text-left space-y-2 pt-2 border-t border-gray-200">
      <p className="text-sm font-medium text-gray-700">Meus pedidos</p>
      {orders.map((order) => {
        const expanded = expandedId === order.id
        return (
          <div key={order.id} className="border border-gray-200 rounded-lg p-2 text-xs space-y-1.5">
            <button
              type="button"
              onClick={() => setExpandedId(expanded ? null : order.id)}
              className="w-full flex items-center justify-between text-left"
            >
              <span className="text-gray-600">
                {order.module_name} — {new Date(order.created_at).toLocaleDateString('pt-BR')}
              </span>
              <span className="flex items-center gap-1">
                <span className="font-medium text-gray-900">{ORDER_STATUS_LABELS[order.status] || order.status}</span>
                <span className="text-gray-400">{expanded ? '▲' : '▼'}</span>
              </span>
            </button>

            {expanded && (
              <div className="space-y-2 pt-1.5 border-t border-gray-100">
                {order.status_events.length > 0 && (
                  <div className="space-y-0.5">
                    {order.status_events.map((event) => (
                      <p key={event.id} className="text-gray-500">
                        <span className="font-medium text-gray-700">{ORDER_STATUS_LABELS[event.status] || event.status}</span>
                        {' — '}
                        {new Date(event.created_at).toLocaleString('pt-BR')}
                      </p>
                    ))}
                  </div>
                )}
                {order.items.length > 0 && (
                  <table className="w-full text-xs">
                    <tbody>
                      {order.items.map((oi) => (
                        <tr key={oi.id} className="border-b border-gray-100 last:border-0">
                          <td className="py-1 text-gray-700">
                            {oi.quantity}x {oi.name}
                          </td>
                          <td className="py-1 text-right text-gray-700 font-medium">R$ {oi.subtotal.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {order.amount != null && (
                  <p className="text-gray-700 font-medium">Total: R$ {order.amount.toFixed(2)}</p>
                )}
                {Object.entries(order.data).map(([key, value]) => (
                  <p key={key} className="text-gray-600">
                    <span className="font-medium">{key}:</span> {String(value)}
                  </p>
                ))}
              </div>
            )}

            <div className="flex items-center gap-3">
              {cart && order.items.length > 0 && (
                <button
                  type="button"
                  onClick={() => handleReorder(order)}
                  className="text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  ↻ Pedir novamente
                </button>
              )}
              {CANCELABLE_ORDER_STATUSES.has(order.status) && (
                <button
                  type="button"
                  onClick={() => handleCancel(order)}
                  disabled={cancellingId === order.id}
                  className="text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                >
                  {cancellingId === order.id ? 'Cancelando...' : '✕ Cancelar pedido'}
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

interface LoggedInEndUser {
  full_name: string
  email?: string
  phone?: string | null
  address?: string | null
  birth_date?: string | null
  referral_code?: string | null
}

function EndUserAuthWidget({ appId }: { appId: string }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [loggedInUser, setLoggedInUser] = useState<LoggedInEndUser | null>(null)
  const [endUserToken, setEndUserToken] = useState<string | null>(null)
  const [editingProfile, setEditingProfile] = useState(false)
  const [profileFullName, setProfileFullName] = useState('')
  const [profilePhone, setProfilePhone] = useState('')
  const [profileAddress, setProfileAddress] = useState('')
  const [profileBirthDate, setProfileBirthDate] = useState('')
  const [referralCodeFromUrl, setReferralCodeFromUrl] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)
  const [exportingData, setExportingData] = useState(false)
  const [deletingAccount, setDeletingAccount] = useState(false)

  // Restaura a sessão salva no localStorage, e trata o redirect de volta do
  // login via Facebook (?fb_token=... na URL) buscando os dados do usuário.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const fbToken = params.get('fb_token')
    const ref = params.get('ref')
    if (ref) setReferralCodeFromUrl(ref)

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
        mode === 'register'
          ? { email, password, full_name: fullName, ...(referralCodeFromUrl ? { referral_code: referralCodeFromUrl } : {}) }
          : { email, password }
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

  const handleSaveProfile = async () => {
    if (!endUserToken) return
    if (newPassword && !currentPassword) {
      toast.error('Informe a senha atual pra trocar de senha')
      return
    }
    setSavingProfile(true)
    try {
      const response = await publicApi.put(
        `/api/apps/${appId}/end-users/me`,
        {
          full_name: profileFullName,
          phone: profilePhone,
          address: profileAddress,
          birth_date: profileBirthDate || null,
          ...(newPassword ? { current_password: currentPassword, new_password: newPassword } : {}),
        },
        { headers: { Authorization: `Bearer ${endUserToken}` } }
      )
      setLoggedInUser(response.data)
      localStorage.setItem(endUserSessionKey(appId), JSON.stringify({ token: endUserToken, user: response.data }))
      setEditingProfile(false)
      setCurrentPassword('')
      setNewPassword('')
      toast.success('Perfil atualizado!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar perfil')
    } finally {
      setSavingProfile(false)
    }
  }

  const handleExportData = async () => {
    if (!endUserToken) return
    setExportingData(true)
    try {
      const response = await publicApi.get(`/api/apps/${appId}/end-users/me/export`, {
        headers: { Authorization: `Bearer ${endUserToken}` },
      })
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'meus-dados.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao exportar seus dados')
    } finally {
      setExportingData(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (!endUserToken) return
    if (!window.confirm('Tem certeza? Sua conta e dados pessoais serão apagados e não podem ser recuperados.')) return
    setDeletingAccount(true)
    try {
      await publicApi.delete(`/api/apps/${appId}/end-users/me`, {
        headers: { Authorization: `Bearer ${endUserToken}` },
      })
      localStorage.removeItem(endUserSessionKey(appId))
      setLoggedInUser(null)
      setEndUserToken(null)
      toast.success('Sua conta foi removida.')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao excluir sua conta')
    } finally {
      setDeletingAccount(false)
    }
  }

  if (loggedInUser) {
    return (
      <div className="text-center space-y-3 mt-8">
        <p className="text-sm text-gray-700">Olá, <span className="font-semibold">{loggedInUser.full_name}</span>!</p>
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => {
              setProfileFullName(loggedInUser.full_name || '')
              setProfilePhone(loggedInUser.phone || '')
              setProfileAddress(loggedInUser.address || '')
              setProfileBirthDate(loggedInUser.birth_date || '')
              setEditingProfile((v) => !v)
            }}
            className="text-xs text-indigo-600 hover:text-indigo-700"
          >
            {editingProfile ? 'Cancelar' : 'Editar perfil'}
          </button>
          <button
            type="button"
            onClick={() => {
              localStorage.removeItem(endUserSessionKey(appId))
              setLoggedInUser(null)
              setEndUserToken(null)
              setEmail('')
              setPassword('')
              setFullName('')
              setEditingProfile(false)
            }}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Sair
          </button>
        </div>

        {editingProfile && (
          <div className="text-left space-y-2 border border-gray-200 rounded-lg p-3">
            <input
              type="text"
              value={profileFullName}
              onChange={(e) => setProfileFullName(e.target.value)}
              placeholder="Nome"
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <input
              type="text"
              value={profilePhone}
              onChange={(e) => setProfilePhone(e.target.value)}
              placeholder="Telefone"
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <textarea
              value={profileAddress}
              onChange={(e) => setProfileAddress(e.target.value)}
              placeholder="Endereço padrão (usado pra pré-preencher pedidos)"
              rows={2}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <label className="block text-xs text-gray-500">
              Data de nascimento (ganhe um cupom de aniversário 🎂)
              <input
                type="date"
                value={profileBirthDate}
                onChange={(e) => setProfileBirthDate(e.target.value)}
                className="w-full mt-0.5 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </label>
            <p className="text-[11px] text-gray-400 pt-1">Trocar senha (opcional)</p>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Senha atual"
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Nova senha"
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <button
              type="button"
              onClick={handleSaveProfile}
              disabled={savingProfile}
              className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {savingProfile ? 'Salvando...' : 'Salvar perfil'}
            </button>
          </div>
        )}

        {loggedInUser.referral_code && (
          <div className="text-left border border-dashed border-indigo-200 rounded-lg p-3 text-xs text-gray-600 space-y-1">
            <p>🤝 Indique um amigo e ganhe cupom quando ele comprar pela primeira vez!</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-gray-50 px-2 py-1 rounded truncate">
                {typeof window !== 'undefined' ? `${window.location.origin}${window.location.pathname}?ref=${loggedInUser.referral_code}` : ''}
              </code>
              <button
                type="button"
                onClick={() => {
                  const link = `${window.location.origin}${window.location.pathname}?ref=${loggedInUser.referral_code}`
                  navigator.clipboard.writeText(link)
                  toast.success('Link copiado!')
                }}
                className="text-indigo-600 hover:text-indigo-700 font-medium flex-shrink-0"
              >
                Copiar
              </button>
            </div>
          </div>
        )}

        {endUserToken && <MyOrders appId={appId} token={endUserToken} />}

        <div className="border-t border-gray-100 pt-3 flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={handleExportData}
            disabled={exportingData}
            className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50"
          >
            {exportingData ? 'Baixando...' : 'Baixar meus dados'}
          </button>
          <button
            type="button"
            onClick={handleDeleteAccount}
            disabled={deletingAccount}
            className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            {deletingAccount ? 'Excluindo...' : 'Excluir minha conta'}
          </button>
        </div>
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

const GATEWAY_CREDENTIAL_KEYS: Record<string, string[]> = {
  mercado_pago: ['access_token'],
  paypal: ['client_id', 'client_secret'],
  pagseguro: ['token'],
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
  customCss,
  navigationStyle = 'hamburger',
  homeScreenStyle = 'content',
  editable = false,
  onModulesChange,
  onConfigureModule,
  configVersion,
}: AppRuntimeProps) {
  const [configs, setConfigs] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [cartOpen, setCartOpen] = useState(false)
  const [selectedModule, setSelectedModule] = useState(homeModule || activeModules[0] || '')
  const [showIconGridHome, setShowIconGridHome] = useState(homeScreenStyle === 'icon_grid')

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

  useEffect(() => {
    setShowIconGridHome(homeScreenStyle === 'icon_grid')
  }, [homeScreenStyle])

  const moduleByName = new Map(modules.map((m) => [m.name, m]))
  const isHomeScreen = selectedModule === (homeModule || activeModules[0])

  const goHome = () => {
    setSelectedModule(homeModule || activeModules[0] || '')
    setShowIconGridHome(homeScreenStyle === 'icon_grid')
    setMenuOpen(false)
  }

  const selectModule = (name: string) => {
    setSelectedModule(name)
    setShowIconGridHome(false)
    setMenuOpen(false)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = activeModules.indexOf(String(active.id))
    const newIndex = activeModules.indexOf(String(over.id))
    if (oldIndex === -1 || newIndex === -1) return
    onModulesChange?.(arrayMove(activeModules, oldIndex, newIndex))
  }

  const content = (
    <div className="contents" style={{ fontFamily: fontFamily || undefined }}>
      {customCss && <style dangerouslySetInnerHTML={{ __html: sanitizeCustomCss(customCss) }} />}
      <div className="h-10 flex items-center justify-between px-3" style={{ backgroundColor: primaryColor }}>
        {navigationStyle === 'bottom_tabs' ? (
          <span className="w-4" />
        ) : (
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className="text-white text-lg leading-none"
            aria-label="Abrir menu"
          >
            ☰
          </button>
        )}
        <button type="button" onClick={goHome} className="flex items-center justify-center min-w-0">
          {logoUrl ? (
            <img src={logoUrl} alt={appName} className="h-6 object-contain" />
          ) : (
            <span className="text-white text-sm font-semibold truncate">{appName}</span>
          )}
        </button>
        {mode === 'public' ? <InstallPwaButton /> : <span className="w-4" />}
      </div>

      {isHomeScreen && homeImageUrl && (
        <img src={homeImageUrl} alt="" className="w-full h-32 object-cover shrink-0" />
      )}

      <div
        className={`min-h-[320px] p-4 ${navigationStyle === 'bottom_tabs' ? 'pb-20' : ''}`}
        style={{ borderTop: `2px solid ${secondaryColor}` }}
      >
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : activeModules.length === 0 ? (
          <p className="text-sm text-gray-400 italic text-center mt-8">Nenhum módulo ativo ainda</p>
        ) : showIconGridHome ? (
          <IconGridHomeScreen
            modules={modules}
            activeModules={activeModules}
            configs={configs}
            primaryColor={primaryColor}
            onSelect={selectModule}
          />
        ) : (
          <div key={selectedModule} className="module-fade-in">
            {selectedModule in LIST_MODULES ? (
              <ListModuleContent
                mode={mode}
                appId={appId}
                moduleName={selectedModule}
                layout={configs[selectedModule]?.layout === 'grid' ? 'grid' : 'list'}
                cartEnabled={mode === 'public' && CART_ENABLED_MODULES.includes(selectedModule)}
                horarioFuncionamento={configs['pagamento_entrega']?.horario_funcionamento}
                availableGateways={PAYMENT_GATEWAY_MODULES.filter(
                  (gw) =>
                    activeModules.includes(gw) &&
                    GATEWAY_CREDENTIAL_KEYS[gw].every((key) => configs[gw]?.[key])
                )}
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
            ) : selectedModule === 'reserva_mesa' ? (
              <TableReservationWidget
                appId={appId}
                moduleName={selectedModule}
                settings={configs[selectedModule]}
              />
            ) : selectedModule === 'login_cadastro' ? (
              <EndUserAuthWidget appId={appId} />
            ) : selectedModule === 'cartao_fidelidade' ? (
              <LoyaltyBalance appId={appId} settings={configs[selectedModule]} />
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
                        selected={!showIconGridHome && selectedModule === name}
                        onSelect={() => selectModule(name)}
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
                const selected = !showIconGridHome && selectedModule === name
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => selectModule(name)}
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

      {navigationStyle === 'bottom_tabs' && activeModules.length > 0 && (
        <BottomTabBar
          modules={modules}
          activeModules={activeModules}
          configs={configs}
          selected={showIconGridHome ? '' : selectedModule}
          primaryColor={primaryColor}
          onSelect={selectModule}
        />
      )}

      {mode === 'public' && (
        <>
          <CartButton
            onClick={() => setCartOpen(true)}
            color={primaryColor}
            raised={navigationStyle === 'bottom_tabs'}
          />
          <CartDrawer
            appId={appId}
            open={cartOpen}
            onClose={() => setCartOpen(false)}
            freteRegras={configs['calculo_frete']?.regras}
            pontosRetirada={configs['pagamento_entrega']?.pontos_retirada}
            janelaHorarios={configs['pagamento_entrega']?.janela_horarios}
            availableGateways={PAYMENT_GATEWAY_MODULES.filter(
              (gw) =>
                activeModules.includes(gw) &&
                GATEWAY_CREDENTIAL_KEYS[gw].every((key) => configs[gw]?.[key])
            )}
          />
        </>
      )}
    </div>
  )

  return mode === 'public' ? <CartProvider appId={appId}>{content}</CartProvider> : content
}
