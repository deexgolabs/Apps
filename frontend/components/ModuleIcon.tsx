'use client'

import { DEFAULT_MODULE_ICON, MODULE_VECTOR_ICONS, resolveIconName } from '@/lib/moduleIcons'

interface ModuleIconProps {
  moduleName: string
  config?: { icon?: string; icon_name?: string } | undefined
  color?: string
  size?: number
  badge?: boolean
  className?: string
}

// Resolve o ícone de um módulo com a mesma prioridade em todo lugar que exibe
// um: ícone vetorial escolhido > emoji escolhido > ícone vetorial padrão do
// módulo. Centraliza o que antes era uma cadeia de fallback repetida em
// AppRuntime/AddModulePanel/assistente de criação.
export default function ModuleIcon({ moduleName, config, color = '#4F46E5', size = 18, badge = true, className = '' }: ModuleIconProps) {
  const VectorIcon = config?.icon_name ? resolveIconName(config.icon_name) : undefined
  const emoji = !VectorIcon ? config?.icon : undefined
  const FallbackIcon = MODULE_VECTOR_ICONS[moduleName] || DEFAULT_MODULE_ICON

  const content = VectorIcon ? (
    <VectorIcon size={size} color={color} strokeWidth={2} />
  ) : emoji ? (
    <span style={{ fontSize: size }} className="leading-none">{emoji}</span>
  ) : (
    <FallbackIcon size={size} color={color} strokeWidth={2} />
  )

  if (!badge) return content

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full shrink-0 ${className}`}
      style={{ backgroundColor: `${color}1A`, width: size * 2, height: size * 2 }}
    >
      {content}
    </span>
  )
}
