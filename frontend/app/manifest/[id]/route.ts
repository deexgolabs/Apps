import { NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const response = await fetch(`${API_URL}/api/apps/${id}/public`)

  if (!response.ok) {
    return NextResponse.json({ error: 'App not found or not published' }, { status: 404 })
  }

  const app = await response.json()
  const config = app.config || {}

  const manifest: Record<string, any> = {
    name: app.name,
    short_name: app.name,
    start_url: `/app/${id}`,
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: config.primary_color || '#4F46E5',
  }

  if (config.icon_url) {
    // Não há pipeline de redimensionamento de imagem no projeto — declaramos vários
    // tamanhos apontando para a mesma URL (o navegador reamostra a partir dela) em vez
    // de gerar assets realmente redimensionados. Resolve a maioria dos casos de
    // instalação de PWA sem exigir upload de múltiplos arquivos.
    const sizes = ['72x72', '96x96', '128x128', '144x144', '152x152', '192x192', '384x384', '512x512']
    manifest.icons = [
      ...sizes.map((size) => ({ src: config.icon_url, sizes: size, type: 'image/png', purpose: 'any' })),
      { src: config.icon_url, sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ]
  }

  return NextResponse.json(manifest, {
    headers: { 'Content-Type': 'application/manifest+json' },
  })
}
