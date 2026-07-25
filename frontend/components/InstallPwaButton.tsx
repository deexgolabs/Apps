'use client'

import { useEffect, useState } from 'react'

/** Botão "Instalar app" pro cliente final da loja publicada. No Chrome/Edge/Android
 * usa o evento beforeinstallprompt nativo; no iOS Safari (que não dispara esse
 * evento) mostra um passo-a-passo manual, já que lá instalar é sempre via
 * Compartilhar → Adicionar à Tela de Início. Some sozinho se o app já estiver
 * rodando instalado (display-mode: standalone). */
export default function InstallPwaButton() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null)
  const [isStandalone, setIsStandalone] = useState(true)
  const [isIos, setIsIos] = useState(false)
  const [showIosHint, setShowIosHint] = useState(false)

  useEffect(() => {
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone === true
    setIsStandalone(standalone)
    setIsIos(/iphone|ipad|ipod/i.test(window.navigator.userAgent))

    const handler = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  if (isStandalone) return null
  if (!deferredPrompt && !isIos) return null

  const handleClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt()
      const { outcome } = await deferredPrompt.userChoice
      if (outcome === 'accepted') setDeferredPrompt(null)
    } else if (isIos) {
      setShowIosHint(true)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className="text-white text-xs font-medium bg-black/20 px-2 py-1 rounded flex items-center gap-1 shrink-0"
        aria-label="Instalar aplicativo"
      >
        <span aria-hidden>⬇</span> Instalar
      </button>

      {showIosHint && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-end justify-center"
          onClick={() => setShowIosHint(false)}
        >
          <div
            className="bg-white w-full max-w-md rounded-t-xl p-4 text-sm text-gray-700"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-medium mb-2 text-gray-900">Instalar este app no iPhone</p>
            <p className="mb-1">1. Toque no ícone de compartilhar (□↑) na barra do Safari.</p>
            <p>2. Escolha &quot;Adicionar à Tela de Início&quot;.</p>
            <button
              type="button"
              onClick={() => setShowIosHint(false)}
              className="mt-3 text-indigo-600 font-medium"
            >
              Entendi
            </button>
          </div>
        </div>
      )}
    </>
  )
}
