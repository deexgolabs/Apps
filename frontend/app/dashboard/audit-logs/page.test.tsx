import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import AuditLogsPage from './page'
import api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AuditLogsPage', () => {
  it('shows an empty state when there are no log entries', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] })
    render(<AuditLogsPage />)

    expect(await screen.findByText('Nenhuma ação registrada ainda.')).toBeInTheDocument()
  })

  it('renders log entries with translated action labels and details', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [
        {
          id: 1,
          app_id: 5,
          app_name: 'Minha Loja',
          action: 'update_app_status',
          target: 'app:5:Minha Loja',
          details: 'status: draft -> published',
          created_at: '2026-07-31T10:00:00Z',
        },
        {
          id: 2,
          app_id: null,
          app_name: null,
          action: 'enable_2fa',
          target: 'dono@example.com',
          details: null,
          created_at: '2026-07-31T09:00:00Z',
        },
      ],
    })

    render(<AuditLogsPage />)

    await waitFor(() => expect(screen.getByText(/Mudou o status do app/)).toBeInTheDocument())
    expect(screen.getByText(/Minha Loja/)).toBeInTheDocument()
    expect(screen.getByText('status: draft -> published')).toBeInTheDocument()
    expect(screen.getByText('Ativou o 2FA')).toBeInTheDocument()
  })
})
