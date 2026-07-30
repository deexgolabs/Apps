import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import NewAppPage from './page'
import api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/store/useAppStore', () => ({
  useAppStore: (selector: any) => selector({ addApp: vi.fn() }),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.get).mockResolvedValue({ data: [] })
})

describe('NewAppPage template preview', () => {
  it('shows a placeholder hint before hovering any template', async () => {
    render(<NewAppPage />)
    fireEvent.change(screen.getByPlaceholderText('Meu App Incrível'), { target: { value: 'Minha Loja' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    expect(await screen.findByText('Escolha um Template')).toBeInTheDocument()
    expect(screen.getByText('Passe o mouse sobre um template pra ver a prévia aqui.')).toBeInTheDocument()
  })

  it('shows the hovered template preview and switches when hovering another', async () => {
    render(<NewAppPage />)
    fireEvent.change(screen.getByPlaceholderText('Meu App Incrível'), { target: { value: 'Minha Loja' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))
    await screen.findByText('Escolha um Template')

    fireEvent.mouseEnter(screen.getByRole('button', { name: /Restaurante/ }))
    expect(await screen.findByText('Prévia: Restaurante')).toBeInTheDocument()
    expect(screen.getByText('Módulos incluídos no template "Restaurante":')).toBeInTheDocument()

    fireEvent.mouseEnter(screen.getByRole('button', { name: /^🛍️/ }))
    expect(await screen.findByText('Prévia: Loja')).toBeInTheDocument()
  })

  it('keeps previewing the selected template after the mouse leaves', async () => {
    render(<NewAppPage />)
    fireEvent.change(screen.getByPlaceholderText('Meu App Incrível'), { target: { value: 'Minha Loja' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))
    await screen.findByText('Escolha um Template')

    const restauranteBtn = screen.getByRole('button', { name: /Restaurante/ })
    fireEvent.mouseEnter(restauranteBtn)
    fireEvent.click(restauranteBtn)
    fireEvent.mouseLeave(restauranteBtn)

    expect(await screen.findByText('Prévia: Restaurante')).toBeInTheDocument()
  })
})
