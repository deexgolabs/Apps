import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import BillingPage from './page'
import { useAuthStore } from '@/store/useAuthStore'
import type { User } from '@/types'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(),
}))

const baseUser: User = {
  id: 1,
  email: 'dono@example.com',
  full_name: 'Dono Teste',
  plan: 'pro',
  plan_expires_at: '2026-08-29T00:00:00Z',
  is_active: true,
  is_verified: true,
  is_admin: false,
  bonus_app_slots: 0,
  created_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('BillingPage renewal', () => {
  it('shows the renewal date for the current paid plan', () => {
    useAuthStore.setState({ user: baseUser })
    render(<BillingPage />)

    expect(screen.getByText(/Renova até/)).toBeInTheDocument()
  })

  it('offers renewal buttons (not hidden) for the current plan', () => {
    useAuthStore.setState({ user: baseUser })
    render(<BillingPage />)

    expect(screen.getByRole('button', { name: 'Renovar via Mercado Pago' })).toBeInTheDocument()
  })

  it('offers subscribe buttons for a plan the user is not on', () => {
    useAuthStore.setState({ user: baseUser })
    render(<BillingPage />)

    expect(screen.getByRole('button', { name: 'Assinar via Mercado Pago' })).toBeInTheDocument()
  })

  it('does not show a renewal date for the free plan', () => {
    useAuthStore.setState({ user: { ...baseUser, plan: 'free', plan_expires_at: null } })
    render(<BillingPage />)

    expect(screen.queryByText(/Renova até/)).not.toBeInTheDocument()
  })
})
