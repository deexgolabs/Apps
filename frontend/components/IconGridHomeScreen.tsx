'use client'

import ModuleIcon from '@/components/ModuleIcon'
import type { Module } from '@/types'

/** Tela inicial estilo "launcher" de celular — mostra os módulos ativos como
 * ícones em grade (usando o mesmo ícone/emoji já configurado pra cada um em
 * ModuleSettingsModal), em vez de abrir direto no conteúdo do módulo inicial. */
export default function IconGridHomeScreen({
  modules,
  activeModules,
  configs,
  primaryColor,
  onSelect,
}: {
  modules: Module[]
  activeModules: string[]
  configs: Record<string, any>
  primaryColor: string
  onSelect: (name: string) => void
}) {
  const moduleByName = new Map(modules.map((m) => [m.name, m]))

  return (
    <div className="grid grid-cols-4 gap-3">
      {activeModules.map((name) => {
        const module = moduleByName.get(name)
        const label = configs[name]?.display_name || module?.description || name
        return (
          <button
            key={name}
            type="button"
            onClick={() => onSelect(name)}
            className="flex flex-col items-center gap-1 text-center"
          >
            <span
              className="w-12 h-12 rounded-2xl flex items-center justify-center"
              style={{ backgroundColor: `${primaryColor}1A` }}
            >
              <ModuleIcon moduleName={name} config={configs[name]} color={primaryColor} size={22} />
            </span>
            <span className="text-[11px] text-gray-600 leading-tight line-clamp-2">{label}</span>
          </button>
        )
      })}
    </div>
  )
}
