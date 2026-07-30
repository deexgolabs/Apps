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
    name: 'blog',
    description: 'Blog ou área de notícias com múltiplos posts',
    category: 'content',
    icon_url: null,
    requires_plan: 'free',
    features: [],
  },
]

const newPost: ModuleItem = {
  id: 1,
  app_id: 1,
  module_name: 'blog',
  category_id: null,
  name: 'Primeiro post do blog',
  description: 'Um resumo rápido da novidade.',
  price: null,
  image_url: null,
  extra: { body: 'Conteúdo completo do primeiro post.', published_at: '2026-07-15' },
  order: 0,
  stock: null,
  variations: [],
  avg_rating: null,
  review_count: 0,
}

const olderPost: ModuleItem = {
  ...newPost,
  id: 2,
  name: 'Post antigo',
  description: 'Um post mais antigo.',
  extra: { body: 'Conteúdo do post mais antigo.', published_at: '2026-06-01' },
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
    if (url.includes('/items')) return Promise.resolve({ data: [olderPost, newPost] })
    if (url.includes('/api/modules')) return Promise.resolve({ data: modules })
    return Promise.resolve({ data: {} })
  })
})

describe('AppRuntime blog module (public mode)', () => {
  it('lists posts sorted by published date descending, with excerpt and date', async () => {
    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Blog Teste"
        modules={modules}
        activeModules={['blog']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="blog"
      />
    )

    await waitFor(() => expect(screen.getByText('Primeiro post do blog')).toBeInTheDocument())
    expect(screen.getByText('Post antigo')).toBeInTheDocument()

    const newerEl = screen.getByText('Primeiro post do blog')
    const olderEl = screen.getByText('Post antigo')
    // bitmask 4 = Node.DOCUMENT_POSITION_FOLLOWING: newerEl comes before olderEl in the DOM
    expect(newerEl.compareDocumentPosition(olderEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

    expect(screen.getByText('Um resumo rápido da novidade.')).toBeInTheDocument()
    expect(screen.getByText(/15\/07\/2026/)).toBeInTheDocument()
  })

  it('expands a post on click to reveal the full body', async () => {
    render(
      <AppRuntime
        mode="public"
        appId="1"
        appName="App Blog Teste"
        modules={modules}
        activeModules={['blog']}
        primaryColor="#4F46E5"
        secondaryColor="#10B981"
        logoUrl=""
        homeModule="blog"
      />
    )

    await waitFor(() => expect(screen.getByText('Primeiro post do blog')).toBeInTheDocument())
    expect(screen.queryByText('Conteúdo completo do primeiro post.')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Primeiro post do blog'))

    await waitFor(() =>
      expect(screen.getByText('Conteúdo completo do primeiro post.')).toBeInTheDocument()
    )
  })
})
