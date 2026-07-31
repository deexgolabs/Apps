import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReferralsPage from './page'
import api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })

const baseInfo = {
  referral_code: 'ABC123',
  referral_link: 'https://apps-wheat-chi.vercel.app/auth/register?ref=ABC123',
  bonus_app_slots: 1,
  referred_count: 3,
  activated_count: 2,
  referred: [
    { full_name: 'Maria Silva', is_verified: true, created_at: '2026-01-01T00:00:00Z' },
    { full_name: 'João Souza', is_verified: false, created_at: '2026-01-02T00:00:00Z' },
  ],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ReferralsPage', () => {
  it('shows the referral link, stats and referred list', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: baseInfo })
    render(<ReferralsPage />)

    expect(await screen.findByDisplayValue(baseInfo.referral_link)).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('Maria Silva')).toBeInTheDocument()
    expect(screen.getByText('Confirmado')).toBeInTheDocument()
    expect(screen.getByText('João Souza')).toBeInTheDocument()
    expect(screen.getByText('Aguardando confirmação')).toBeInTheDocument()
  })

  it('copies the referral link when the button is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: baseInfo })
    render(<ReferralsPage />)

    const copyBtn = await screen.findByRole('button', { name: 'Copiar' })
    fireEvent.click(copyBtn)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(baseInfo.referral_link)
    expect(await screen.findByRole('button', { name: 'Copiado!' })).toBeInTheDocument()
  })

  it('shows an empty state when nobody was referred yet', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { ...baseInfo, referred_count: 0, referred: [] } })
    render(<ReferralsPage />)

    expect(await screen.findByText('Ninguém se cadastrou com seu link ainda.')).toBeInTheDocument()
  })
})
