'use client'

import type { ReactNode } from 'react'

interface PhoneFrameProps {
  children: ReactNode
  platform?: 'android' | 'ios'
}

/** Moldura de celular usada pelo preview (AppPreview) e pelo assistente de
 * criação, em proporção real fixa. O conteúdo passado como children rola
 * internamente (a moldura tem altura fixa, não cresce com o conteúdo).
 * `platform` só troca decorações visuais (notch/home indicator no iOS,
 * barra de navegação no Android) — puramente estético, não afeta o app. */
export default function PhoneFrame({ children, platform = 'android' }: PhoneFrameProps) {
  const isIos = platform === 'ios'

  return (
    <div
      className={`mx-auto w-[280px] h-[600px] border-8 border-gray-800 bg-gray-50 shadow-xl overflow-hidden flex flex-col relative ${
        isIos ? 'rounded-[2.5rem]' : 'rounded-2xl'
      }`}
    >
      {isIos && (
        <div className="absolute top-1 left-1/2 -translate-x-1/2 w-20 h-5 bg-gray-900 rounded-full z-10 pointer-events-none" />
      )}

      <div className="flex-1 min-h-0 overflow-y-auto relative flex flex-col">
        {children}
        {isIos && (
          <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-24 h-1 bg-gray-900/80 rounded-full pointer-events-none" />
        )}
      </div>

      {!isIos && (
        <div className="h-6 bg-gray-100 border-t border-gray-200 flex items-center justify-center gap-8 shrink-0 pointer-events-none">
          <span className="w-2.5 h-2.5 border-2 border-gray-400 rotate-45" />
          <span className="w-2.5 h-2.5 rounded-full border-2 border-gray-400" />
          <span className="w-2.5 h-2.5 border-2 border-gray-400 rounded-sm" />
        </div>
      )}
    </div>
  )
}
