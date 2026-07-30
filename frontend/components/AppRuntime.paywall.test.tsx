import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import AppRuntime from './AppRuntime'
import { publicApi } from '@/lib/api'
import { endUserSessionKey } from '@/lib/endUserAuth'
import type { Module, ModuleItem } from '@/types'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn(), put: vi.fn() },
  publicApi: { get: vi.fn(), post: vi.fn(), delete: vi.fn(), put: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

const modules: Module[] = [
  {
    id: 1,
    name: 'conteudo_pago',
    description: 'Conteúdo exclusivo desbloqueado mediante pagamento (paywall)',
    category: 'monetization',
    icon_url: null,
    requires_plan: 'free',
    features: [],
  },
  {
    id: 2,
    name: 'mercado_pago',
    description: 'Pagamento via Mercado Pago',
    category: 'payments',
    icon_url: null,
    requires_plan: 'free',
    features: [],
  },
]

const lockedItem: ModuleItem = {
  id: 1,
  app_id: 1,
  module_name: 'conteudo_pago',
  category_id: null,
  name: 'Artigo Exclusivo',
  description: 'Uma prévia gratuita do artigo.',
  price: 15,
  image_url: null,
  extra: { body: 'Conteúdo completo só pra assinantes.' },
  order: 0,
  stock: null,
  variations: [],
  avg_rating: null,
  review_count: 0,
}

function setEndUserSession(appId: string) {
  localStorage.setItem(endUserSessionKey(appId), JSON.stringify({ token: 'fake-token', user: { id: 1 } }))
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockReturnValue({
      matches: false,
      media: '',
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  })
})

describe('AppRuntime conteudo_pago module (public mode)', () => {
  it('shows an unlock button with price for a locked item, not the full body', async () => {
    vi.mocked(publicApi.get).mockImplementation((url: string) => {
      if (url.includes('/public/module-configs')) return Promise.resolve({ data: {} })
      if (url.includes('/unlocked-items')) return Promise.resolve({ data: [] })
      if (url.includes('/items')) return Promise.resolve({ data: [lockedItem] })
      if (url.includes('/api/modules')) return Promise.resolve({ data: modules })
      return Promise.resolve({ data: {} })
    })
    setEndUserSession('1')

    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Paywall Teste"
        modules={modules}
        activeModules={['conteudo_pago', 'mercado_pago']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="conteudo_pago"
      />
    )

    await waitFor(() => expect(screen.getByText('Artigo Exclusivo')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Artigo Exclusivo'))

    await waitFor(() => expect(screen.getByText(/Desbloquear por R\$ 15\.00/)).toBeInTheDocument())
    expect(screen.queryByText('Conteúdo completo só pra assinantes.')).not.toBeInTheDocument()
  })

  it('shows the full body for an already unlocked item', async () => {
    vi.mocked(publicApi.get).mockImplementation((url: string) => {
      if (url.includes('/public/module-configs')) return Promise.resolve({ data: {} })
      if (url.includes('/unlocked-items')) return Promise.resolve({ data: [1] })
      if (url.includes('/items')) return Promise.resolve({ data: [lockedItem] })
      if (url.includes('/api/modules')) return Promise.resolve({ data: modules })
      return Promise.resolve({ data: {} })
    })
    setEndUserSession('1')

    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Paywall Teste"
        modules={modules}
        activeModules={['conteudo_pago', 'mercado_pago']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="conteudo_pago"
      />
    )

    await waitFor(() => expect(screen.getByText('Artigo Exclusivo')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Artigo Exclusivo'))

    await waitFor(() =>
      expect(screen.getByText('Conteúdo completo só pra assinantes.')).toBeInTheDocument()
    )
    expect(screen.getByText('🔓 Desbloqueado')).toBeInTheDocument()
  })

  it('starts checkout and shows the "Já paguei" confirmation step on unlock click', async () => {
    vi.mocked(publicApi.get).mockImplementation((url: string) => {
      if (url.includes('/public/module-configs'))
        return Promise.resolve({ data: { mercado_pago: { access_token: 'fake-token' } } })
      if (url.includes('/unlocked-items')) return Promise.resolve({ data: [] })
      if (url.includes('/items')) return Promise.resolve({ data: [lockedItem] })
      if (url.includes('/api/modules')) return Promise.resolve({ data: modules })
      return Promise.resolve({ data: {} })
    })
    vi.mocked(publicApi.post).mockResolvedValue({
      data: { id: 42, checkout_url: 'https://gateway.example/checkout/42' },
    })
    setEndUserSession('1')
    vi.stubGlobal('open', vi.fn())

    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Paywall Teste"
        modules={modules}
        activeModules={['conteudo_pago', 'mercado_pago']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="conteudo_pago"
      />
    )

    await waitFor(() => expect(screen.getByText('Artigo Exclusivo')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Artigo Exclusivo'))
    await waitFor(() => expect(screen.getByText(/Desbloquear por R\$ 15\.00/)).toBeInTheDocument())

    fireEvent.click(screen.getByText(/Desbloquear por R\$ 15\.00/))

    await waitFor(() => expect(screen.getByText('Já paguei')).toBeInTheDocument())
    expect(publicApi.post).toHaveBeenCalledWith(
      '/api/apps/1/modules/conteudo_pago/cart-checkout',
      { items: [{ item_id: 1, quantity: 1 }], gateway: 'mercado_pago' },
      expect.anything()
    )
    expect(window.open).toHaveBeenCalledWith('https://gateway.example/checkout/42', '_blank', 'noopener,noreferrer')
  })
})
