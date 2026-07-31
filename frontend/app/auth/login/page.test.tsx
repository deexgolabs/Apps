import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LoginPage from './page'
import { authService } from '@/lib/auth'

vi.mock('@/lib/auth', () => ({
  authService: { login: vi.fn(), verify2fa: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

const push = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('LoginPage 2FA challenge', () => {
  it('goes straight to the dashboard when 2FA is not required', async () => {
    vi.mocked(authService.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer', user: {} } as any)
    render(<LoginPage />)

    fireEvent.change(screen.getByPlaceholderText('seu@email.com'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'senha123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'))
    expect(authService.verify2fa).not.toHaveBeenCalled()
  })

  it('shows the code challenge screen when 2FA is required, then verifies it', async () => {
    vi.mocked(authService.login).mockResolvedValue({ requires_2fa: true, temp_token: 'temp-abc' } as any)
    vi.mocked(authService.verify2fa).mockResolvedValue({ access_token: 'tok', token_type: 'bearer', user: {} } as any)
    render(<LoginPage />)

    fireEvent.change(screen.getByPlaceholderText('seu@email.com'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'senha123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Verificação em duas etapas')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('000000'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar' }))

    await vi.waitFor(() => expect(authService.verify2fa).toHaveBeenCalledWith('temp-abc', '123456'))
    await vi.waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'))
  })
})
