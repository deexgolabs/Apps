import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import AppRuntime from './AppRuntime'
import { publicApi } from '@/lib/api'
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
    name: 'venda_ingressos',
    description: 'Venda de ingressos para eventos, com data, local e vagas limitadas',
    category: 'events',
    icon_url: null,
    requires_plan: 'free',
    features: [],
  },
]

const laterEvent: ModuleItem = {
  id: 1,
  app_id: 1,
  module_name: 'venda_ingressos',
  category_id: null,
  name: 'Show de fim de ano',
  description: 'Grande festa de encerramento.',
  price: 50,
  image_url: null,
  extra: { data: '2026-12-20', hora: '20:00', location: 'Arena Central' },
  order: 0,
  stock: 100,
  variations: [],
  avg_rating: null,
  review_count: 0,
}

const soonerEvent: ModuleItem = {
  ...laterEvent,
  id: 2,
  name: 'Workshop de verão',
  description: 'Oficina de uma tarde.',
  extra: { data: '2026-08-01', hora: '14:00', location: 'Sala 2' },
  order: 1,
}

beforeEach(() => {
  vi.clearAllMocks()
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
  vi.mocked(publicApi.get).mockImplementation((url: string) => {
    if (url.includes('/public/module-configs')) return Promise.resolve({ data: {} })
    if (url.includes('/items')) return Promise.resolve({ data: [laterEvent, soonerEvent] })
    if (url.includes('/api/modules')) return Promise.resolve({ data: modules })
    return Promise.resolve({ data: {} })
  })
})

describe('AppRuntime venda_ingressos module (public mode)', () => {
  it('lists events sorted by date ascending, with date, time and location', async () => {
    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Eventos Teste"
        modules={modules}
        activeModules={['venda_ingressos']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="venda_ingressos"
      />
    )

    await waitFor(() => expect(screen.getByText('Workshop de verão')).toBeInTheDocument())
    expect(screen.getByText('Show de fim de ano')).toBeInTheDocument()

    const soonerEl = screen.getByText('Workshop de verão')
    const laterEl = screen.getByText('Show de fim de ano')
    expect(soonerEl.compareDocumentPosition(laterEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

    expect(screen.getByText(/01\/08\/2026/)).toBeInTheDocument()
    expect(screen.getByText(/14:00/)).toBeInTheDocument()
    expect(screen.getByText(/Sala 2/)).toBeInTheDocument()
    expect(screen.getAllByText(/R\$ 50\.00/).length).toBeGreaterThan(0)
  })

  it('allows adding a ticket to the cart', async () => {
    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Eventos Teste"
        modules={modules}
        activeModules={['venda_ingressos']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="venda_ingressos"
      />
    )

    await waitFor(() => expect(screen.getByText('Workshop de verão')).toBeInTheDocument())
    const addButtons = screen.getAllByText('+ Adicionar')
    fireEvent.click(addButtons[0])

    await waitFor(() => expect(screen.getByText('1')).toBeInTheDocument())
  })
})
