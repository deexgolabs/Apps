'use client'

import { useState } from 'react'
import ModuleIcon from '@/components/ModuleIcon'
import type { Module } from '@/types'

const PLAN_RANK: Record<string, number> = { free: 0, pro: 1, business: 2 }

function isLocked(module: Module, userPlan: string) {
  return (PLAN_RANK[module.requires_plan] ?? 0) > (PLAN_RANK[userPlan] ?? 0)
}

const CATEGORY_LABELS: Record<string, string> = {
  content: 'Conteúdo',
  communication: 'Comunicação',
  location: 'Localização',
  integration: 'Integrações',
  media: 'Mídia',
  monetization: 'Monetização',
  food: 'Cardápio',
  ecommerce: 'Loja',
  forms: 'Formulários',
  engagement: 'Engajamento',
  payments: 'Pagamentos',
}

const CATEGORY_ORDER = [
  'content', 'food', 'ecommerce', 'forms', 'communication', 'engagement',
  'payments', 'location', 'media', 'integration', 'monetization',
]

interface AddModulePanelProps {
  modules: Module[]
  activeModules: string[]
  userPlan: string
  primaryColor: string
  onAdd: (name: string) => void
}

export default function AddModulePanel({ modules, activeModules, userPlan, primaryColor, onAdd }: AddModulePanelProps) {
  const [search, setSearch] = useState('')
  const available = modules.filter((m) => !activeModules.includes(m.name))

  if (available.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic text-center py-12">
        Todos os módulos do catálogo já estão ativos neste app.
      </p>
    )
  }

  const query = search.trim().toLowerCase()
  const filtered = query
    ? available.filter((m) => m.description.toLowerCase().includes(query))
    : available

  const byCategory = new Map<string, Module[]>()
  for (const module of filtered) {
    const list = byCategory.get(module.category) || []
    list.push(module)
    byCategory.set(module.category, list)
  }

  const orderedCategories = [
    ...CATEGORY_ORDER.filter((c) => byCategory.has(c)),
    ...[...byCategory.keys()].filter((c) => !CATEGORY_ORDER.includes(c)),
  ]

  return (
    <div className="space-y-8">
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Buscar módulo..."
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
      />
      {orderedCategories.length === 0 && (
        <p className="text-sm text-gray-400 italic text-center py-6">Nenhum módulo encontrado para "{search}".</p>
      )}
      {orderedCategories.map((category) => (
        <div key={category}>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            {CATEGORY_LABELS[category] || category}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {byCategory.get(category)!.map((module) => {
              const locked = isLocked(module, userPlan)
              return (
                <button
                  key={module.name}
                  type="button"
                  onClick={() => onAdd(module.name)}
                  disabled={locked}
                  className={`flex items-start gap-3 p-4 rounded-xl border text-left transition ${
                    locked
                      ? 'border-gray-100 bg-gray-50 cursor-not-allowed opacity-60'
                      : 'border-gray-200 hover:border-indigo-400 hover:shadow-sm'
                  }`}
                >
                  <ModuleIcon moduleName={module.name} color={primaryColor} size={20} />
                  <span className="min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{module.description}</span>
                      {locked && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-200 text-gray-500 whitespace-nowrap shrink-0">
                          Requer {module.requires_plan}
                        </span>
                      )}
                    </span>
                    {module.features?.[0] && (
                      <span className="block text-xs text-gray-400 mt-0.5">{module.features[0]}</span>
                    )}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
