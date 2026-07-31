import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SecurityPage from './page'
import api from '@/lib/api'
import { useAuthStore } from '@/store/useAuthStore'
import type { User } from '@/types'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

const baseUser: User = {
  id: 1,
  email: 'dono@example.com',
  full_name: 'Dono Teste',
  plan: 'free',
  plan_expires_at: null,
  is_active: true,
  is_verified: true,
  is_admin: false,
  bonus_app_slots: 0,
  totp_enabled: false,
  created_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('SecurityPage 2FA setup', () => {
  it('shows the activate button when 2FA is off', () => {
    useAuthStore.setState({ user: baseUser })
    render(<SecurityPage />)

    expect(screen.getByRole('button', { name: 'Ativar 2FA' })).toBeInTheDocument()
  })

  it('walks through setup: QR code, confirm code, then shows recovery codes', async () => {
    useAuthStore.setState({ user: baseUser })
    vi.mocked(api.post).mockImplementation((url: string) => {
      if (url === '/api/auth/2fa/setup') {
        return Promise.resolve({ data: { secret: 'ABCD1234', otpauth_url: 'otpauth://totp/x?secret=ABCD1234' } })
      }
      if (url === '/api/auth/2fa/enable') {
        return Promise.resolve({ data: { recovery_codes: ['aaaa-bbbb', 'cccc-dddd'] } })
      }
      return Promise.reject(new Error('unexpected url'))
    })

    render(<SecurityPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Ativar 2FA' }))

    expect(await screen.findByPlaceholderText('Código de 6 dígitos')).toBeInTheDocument()
    expect(screen.getByText('ABCD1234')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('Código de 6 dígitos'), { target: { value: '654321' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar e ativar' }))

    expect(await screen.findByText('aaaa-bbbb')).toBeInTheDocument()
    expect(screen.getByText('cccc-dddd')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/api/auth/2fa/enable', { code: '654321' })
  })

  it('shows the disable form when 2FA is already on', () => {
    useAuthStore.setState({ user: { ...baseUser, totp_enabled: true } })
    render(<SecurityPage />)

    expect(screen.getByText('✓ 2FA ativado na sua conta')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Desativar 2FA' })).toBeInTheDocument()
  })

  it('disables 2FA after entering the password', async () => {
    useAuthStore.setState({ user: { ...baseUser, totp_enabled: true } })
    vi.mocked(api.post).mockResolvedValue({ data: { message: 'ok' } })

    render(<SecurityPage />)
    fireEvent.change(screen.getByPlaceholderText('Digite sua senha pra desativar'), { target: { value: 'senha123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Desativar 2FA' }))

    await vi.waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/api/auth/2fa/disable', { password: 'senha123' })
    )
  })
})
