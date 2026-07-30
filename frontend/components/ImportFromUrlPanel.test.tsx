import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ImportFromUrlPanel from './ImportFromUrlPanel'
import api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  default: { post: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ImportFromUrlPanel', () => {
  it('imports data from a URL and calls onImported with the result', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { name: 'Minha Loja', description: 'A melhor loja', image_url: 'https://exemplo.com/logo.png' },
    })
    const onImported = vi.fn()

    render(<ImportFromUrlPanel appId="1" onImported={onImported} />)
    fireEvent.change(screen.getByPlaceholderText('instagram.com/suamarca'), { target: { value: 'instagram.com/minhaloja' } })
    fireEvent.click(screen.getByRole('button', { name: 'Importar' }))

    await vi.waitFor(() => expect(onImported).toHaveBeenCalledWith({
      name: 'Minha Loja',
      description: 'A melhor loja',
      image_url: 'https://exemplo.com/logo.png',
    }))
    expect(api.post).toHaveBeenCalledWith('/api/apps/1/import-from-url', { url: 'instagram.com/minhaloja' })
  })

  it('does not call the API when the URL field is empty', () => {
    const onImported = vi.fn()
    render(<ImportFromUrlPanel appId="1" onImported={onImported} />)

    fireEvent.click(screen.getByRole('button', { name: 'Importar' }))

    expect(api.post).not.toHaveBeenCalled()
  })
})
