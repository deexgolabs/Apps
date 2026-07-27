import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CustomDomainPanel from './CustomDomainPanel'
import api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn(), put: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

const EMPTY_STATUS = { domain: null, verified: false, verification_host: null, verification_token: null }

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

describe('CustomDomainPanel', () => {
  it('shows an input to save a domain when none is set', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: EMPTY_STATUS })

    render(<CustomDomainPanel appId="1" />)

    expect(await screen.findByPlaceholderText('loja.suamarca.com.br')).toBeInTheDocument()
  })

  it('saves a domain and shows DNS verification instructions', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: EMPTY_STATUS })
    vi.mocked(api.put).mockResolvedValue({
      data: {
        domain: 'loja.exemplo.com',
        verified: false,
        verification_host: '_deexgo-challenge.loja.exemplo.com',
        verification_token: 'abc123',
      },
    })

    render(<CustomDomainPanel appId="1" />)
    const input = await screen.findByPlaceholderText('loja.suamarca.com.br')
    fireEvent.change(input, { target: { value: 'loja.exemplo.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('_deexgo-challenge.loja.exemplo.com')).toBeInTheDocument()
    expect(screen.getByText('abc123')).toBeInTheDocument()
    expect(api.put).toHaveBeenCalledWith('/api/apps/1/custom-domain', { domain: 'loja.exemplo.com' })
  })

  it('shows the verified state and lets the owner remove the domain', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { domain: 'loja.exemplo.com', verified: true, verification_host: null, verification_token: null },
    })
    vi.mocked(api.delete).mockResolvedValue({})

    render(<CustomDomainPanel appId="1" />)
    expect(await screen.findByText('✓ loja.exemplo.com')).toBeInTheDocument()
    expect(screen.getByText('Verificado e ativo')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Remover' }))

    await waitFor(() => expect(api.delete).toHaveBeenCalledWith('/api/apps/1/custom-domain'))
    expect(await screen.findByPlaceholderText('loja.suamarca.com.br')).toBeInTheDocument()
  })

  it('verifying successfully flips the panel to the verified state', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        domain: 'loja.exemplo.com',
        verified: false,
        verification_host: '_deexgo-challenge.loja.exemplo.com',
        verification_token: 'abc123',
      },
    })
    vi.mocked(api.post).mockResolvedValue({
      data: { domain: 'loja.exemplo.com', verified: true, verification_host: null, verification_token: null },
    })

    render(<CustomDomainPanel appId="1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Verificar agora' }))

    expect(await screen.findByText('✓ loja.exemplo.com')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/api/apps/1/custom-domain/verify')
  })
})
