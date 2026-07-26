'use client'

import ModuleIcon from '@/components/ModuleIcon'
import type { Module } from '@/types'

/** Navegação alternativa ao menu hambúrguer — barra fixa embaixo com os
 * módulos ativos como abas (ícone + rótulo curto), estilo apps de
 * delivery/rede social. Escolhida pelo dono na aba Marca do construtor. */
export default function BottomTabBar({
  modules,
  activeModules,
  configs,
  selected,
  primaryColor,
  onSelect,
}: {
  modules: Module[]
  activeModules: string[]
  configs: Record<string, any>
  selected: string
  primaryColor: string
  onSelect: (name: string) => void
}) {
  const moduleByName = new Map(modules.map((m) => [m.name, m]))

  return (
    <div className="absolute bottom-0 left-0 right-0 h-16 bg-white border-t border-gray-200 flex overflow-x-auto z-20">
      {activeModules.map((name) => {
        const module = moduleByName.get(name)
        const label = configs[name]?.display_name || module?.description || name
        const isSelected = selected === name
        const color = isSelected ? primaryColor : '#9CA3AF'
        return (
          <button
            key={name}
            type="button"
            onClick={() => onSelect(name)}
            className="flex-1 min-w-[64px] flex flex-col items-center justify-center gap-0.5 px-1"
          >
            <ModuleIcon moduleName={name} config={configs[name]} color={color} size={18} />
            <span
              className="text-[10px] truncate max-w-[60px]"
              style={{ color, fontWeight: isSelected ? 600 : undefined }}
            >
              {label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
