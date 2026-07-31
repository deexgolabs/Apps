import { describe, expect, it, vi, beforeEach } from 'vitest'
import { generateMetadata } from './page'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('generateMetadata for the public app page (Open Graph)', () => {
  it('builds title/description/OG/twitter tags from the app data, including the logo as image', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        name: 'Pizzaria do João',
        description: 'A melhor pizza da cidade',
        config: { logo_url: 'https://backend.example.com/uploads/logo.png' },
      }),
    }) as any

    const metadata = await generateMetadata({ params: Promise.resolve({ id: '1' }) })

    expect(metadata.title).toBe('Pizzaria do João')
    expect(metadata.description).toBe('A melhor pizza da cidade')
    expect(metadata.manifest).toBe('/manifest/1')
    expect(metadata.openGraph).toMatchObject({
      title: 'Pizzaria do João',
      description: 'A melhor pizza da cidade',
      images: ['https://backend.example.com/uploads/logo.png'],
    })
    expect(metadata.twitter).toMatchObject({
      card: 'summary_large_image',
      images: ['https://backend.example.com/uploads/logo.png'],
    })
  })

  it('falls back to a generic description when the app has none', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, name: 'App Sem Descrição', description: null, config: {} }),
    }) as any

    const metadata = await generateMetadata({ params: Promise.resolve({ id: '1' }) })

    expect(metadata.description).toBe('Confira o app App Sem Descrição')
  })

  it('omits images and uses the summary card when there is no logo', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, name: 'App Sem Logo', description: 'Oi', config: {} }),
    }) as any

    const metadata = await generateMetadata({ params: Promise.resolve({ id: '1' }) })

    expect((metadata.openGraph as any).images).toBeUndefined()
    expect(metadata.twitter).toMatchObject({ card: 'summary' })
  })

  it('falls back to just the manifest when the app is not found', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false }) as any

    const metadata = await generateMetadata({ params: Promise.resolve({ id: '999' }) })

    expect(metadata).toEqual({ manifest: '/manifest/999' })
  })

  it('falls back to just the manifest when the fetch throws', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as any

    const metadata = await generateMetadata({ params: Promise.resolve({ id: '5' }) })

    expect(metadata).toEqual({ manifest: '/manifest/5' })
  })
})
