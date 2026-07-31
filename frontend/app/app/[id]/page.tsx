import type { Metadata } from 'next'
import AppPublicClient from './AppPublicClient'

interface PageProps {
  params: Promise<{ id: string }>
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  const fallback: Metadata = { manifest: `/manifest/${id}` }

  try {
    const response = await fetch(`${API_URL}/api/apps/${id}/public`, { cache: 'no-store' })
    if (!response.ok) return fallback

    const app = await response.json()
    const config = app.config || {}
    const title: string = app.name
    const description: string = app.description || `Confira o app ${app.name}`
    // logo_url já vem absoluta (upload no backend sempre devolve URL completa) --
    // sem logo configurado, não dá pra montar uma URL de imagem confiável sem uma
    // env var de origem do frontend que não existe hoje, então o preview fica só
    // com título/descrição nesse caso (ainda melhor que o antigo, sem nada).
    const images: string[] | undefined = config.logo_url ? [config.logo_url] : undefined

    return {
      title,
      description,
      manifest: `/manifest/${id}`,
      openGraph: {
        title,
        description,
        type: 'website',
        images,
      },
      twitter: {
        card: images ? 'summary_large_image' : 'summary',
        title,
        description,
        images,
      },
    }
  } catch {
    return fallback
  }
}

export default async function PublicAppPage({ params }: PageProps) {
  const { id } = await params
  return <AppPublicClient appId={id} />
}
