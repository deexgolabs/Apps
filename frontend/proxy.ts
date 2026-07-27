import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** Hosts que já servem a plataforma diretamente — nunca tenta resolver
 * domínio próprio pra eles (senão toda navegação normal do dashboard vira
 * uma chamada extra ao backend). */
function isPlatformHost(host: string): boolean {
  const bareHost = host.split(':')[0]
  return (
    bareHost === 'localhost' ||
    bareHost === '127.0.0.1' ||
    bareHost.endsWith('.vercel.app') ||
    bareHost === process.env.NEXT_PUBLIC_PLATFORM_HOST
  )
}

export async function proxy(request: NextRequest) {
  const host = request.headers.get('host') || ''
  const { pathname } = request.nextUrl

  if (isPlatformHost(host) || pathname.startsWith('/_next') || pathname.includes('.')) {
    return NextResponse.next()
  }

  // Domínio próprio: pergunta ao backend a qual app esse host verificado
  // pertence, e reescreve pra rota pública já existente — o resto do site
  // (manifest/[id], /_next, etc.) não muda de comportamento nenhum.
  // Nota: opções de cache do fetch (next.revalidate etc.) não têm efeito
  // dentro do Proxy (Next.js 16) — cada requisição bate direto no backend.
  try {
    const response = await fetch(`${API_URL}/api/resolve-domain?host=${encodeURIComponent(host)}`)
    if (!response.ok) {
      return NextResponse.next()
    }
    const data: { app_id: number } = await response.json()
    const url = request.nextUrl.clone()
    url.pathname = `/app/${data.app_id}${pathname === '/' ? '' : pathname}`
    return NextResponse.rewrite(url)
  } catch {
    return NextResponse.next()
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
