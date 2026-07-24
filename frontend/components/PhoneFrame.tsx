'use client'

import type { ReactNode } from 'react'

/** Moldura de celular usada pelo preview (AppPreview) e pelo assistente de
 * criação, em proporção real fixa. O conteúdo passado como children rola
 * internamente (a moldura tem altura fixa, não cresce com o conteúdo). */
export default function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-[280px] h-[600px] border-8 border-gray-800 rounded-[2rem] bg-gray-50 shadow-xl overflow-hidden flex flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto relative flex flex-col">
        {children}
      </div>
    </div>
  )
}
