import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import AppRuntime from './AppRuntime'
import { publicApi } from '@/lib/api'
import { endUserSessionKey } from '@/lib/endUserAuth'
import type { Module } from '@/types'

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
    name: 'login_cadastro',
    description: 'Cadastro/login do cliente final',
    category: 'accounts',
    icon_url: null,
    requires_plan: 'free',
    features: [],
  },
]

function setEndUserSession(appId: string) {
  localStorage.setItem(
    endUserSessionKey(appId),
    JSON.stringify({ token: 'fake-token', user: { id: 1, full_name: 'Cliente Teste' } })
  )
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
  vi.mocked(publicApi.get).mockImplementation((url: string) => {
    if (url.includes('/my-orders')) return Promise.resolve({ data: [] })
    if (url.includes('/end-users/me') && !url.includes('export')) return Promise.resolve({ data: { id: 1, full_name: 'Cliente Teste' } })
    return Promise.resolve({ data: {} })
  })
})

function renderWidget() {
  setEndUserSession('1')
  render(
    <AppRuntime
      mode="public"
      appId="1"
      appName="App LGPD Teste"
      modules={modules}
      activeModules={['login_cadastro']}
      primaryColor="#4F46E5"
      secondaryColor="#10B981"
      logoUrl=""
      homeModule="login_cadastro"
    />
  )
}

describe('AppRuntime login_cadastro LGPD actions', () => {
  it('shows download and delete buttons for a logged in end user', async () => {
    renderWidget()
    await waitFor(() => expect(screen.getByText('Baixar meus dados')).toBeInTheDocument())
    expect(screen.getByText('Excluir minha conta')).toBeInTheDocument()
  })

  it('fetches the export endpoint when "Baixar meus dados" is clicked', async () => {
    vi.mocked(publicApi.get).mockImplementation((url: string) => {
      if (url.includes('/my-orders')) return Promise.resolve({ data: [] })
      if (url.includes('/end-users/me/export')) {
        return Promise.resolve({ data: { profile: { email: 'cliente@example.com' }, orders: [], reviews: [], wishlist: [], loyalty_points: 0 } })
      }
      if (url.includes('/end-users/me')) return Promise.resolve({ data: { id: 1, full_name: 'Cliente Teste' } })
      return Promise.resolve({ data: {} })
    })
    const createObjectURL = vi.fn().mockReturnValue('blob:fake')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })

    renderWidget()
    await waitFor(() => expect(screen.getByText('Baixar meus dados')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Baixar meus dados'))

    await waitFor(() =>
      expect(publicApi.get).toHaveBeenCalledWith(
        '/api/apps/1/end-users/me/export',
        expect.anything()
      )
    )
    expect(createObjectURL).toHaveBeenCalled()
  })

  it('asks for confirmation and calls delete when "Excluir minha conta" is clicked', async () => {
    vi.mocked(publicApi.delete).mockResolvedValue({ data: { message: 'ok' } })
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(true))

    renderWidget()
    await waitFor(() => expect(screen.getByText('Excluir minha conta')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Excluir minha conta'))

    await waitFor(() =>
      expect(publicApi.delete).toHaveBeenCalledWith('/api/apps/1/end-users/me', expect.anything())
    )
    expect(window.confirm).toHaveBeenCalled()
  })

  it('does not call delete if the user cancels the confirmation', async () => {
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(false))

    renderWidget()
    await waitFor(() => expect(screen.getByText('Excluir minha conta')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Excluir minha conta'))

    expect(publicApi.delete).not.toHaveBeenCalled()
  })
})
