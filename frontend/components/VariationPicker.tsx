'use client'

import type { ItemVariation } from '@/types'

function OptionList({
  variations,
  selectedIds,
  onSelect,
  showAsDelta,
}: {
  variations: ItemVariation[]
  selectedIds: number[]
  onSelect: (variation: ItemVariation) => void
  showAsDelta: boolean
}) {
  return (
    <div className="space-y-1.5">
      {variations.map((v) => {
        const outOfStock = v.stock !== null && v.stock <= 0
        const selected = selectedIds.includes(v.id)
        const priceLabel = showAsDelta
          ? v.price === 0
            ? 'sem custo extra'
            : `${v.price > 0 ? '+' : '-'} R$ ${Math.abs(v.price).toFixed(2)}`
          : `R$ ${v.price.toFixed(2)}`
        return (
          <label
            key={v.id}
            className={`flex items-center justify-between gap-2 border rounded px-2 py-1.5 text-xs cursor-pointer ${
              selected ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'
            } ${outOfStock ? 'opacity-40 pointer-events-none' : ''}`}
          >
            <span className="flex items-center gap-1.5">
              <input type="radio" checked={selected} onChange={() => onSelect(v)} disabled={outOfStock} />
              {v.name}
            </span>
            <span className="text-gray-600">{outOfStock ? 'Esgotado' : priceLabel}</span>
          </label>
        )
      })}
    </div>
  )
}

/** Variações sem group_name são um único grupo "solto" (comportamento
 * original: preço absoluto, uma escolha só). Variações com group_name viram
 * grupos combináveis (Fase D) — uma escolha por grupo, preço em delta. */
export default function VariationPicker({
  variations,
  selectedIds,
  onSelect,
}: {
  variations: ItemVariation[]
  selectedIds: number[]
  onSelect: (variation: ItemVariation) => void
}) {
  const ungrouped = variations.filter((v) => !v.group_name)
  const groupNames = Array.from(new Set(variations.filter((v) => v.group_name).map((v) => v.group_name as string)))

  if (groupNames.length === 0) {
    return <OptionList variations={ungrouped} selectedIds={selectedIds} onSelect={onSelect} showAsDelta={false} />
  }

  return (
    <div className="space-y-3">
      {ungrouped.length > 0 && (
        <OptionList variations={ungrouped} selectedIds={selectedIds} onSelect={onSelect} showAsDelta={false} />
      )}
      {groupNames.map((groupName) => (
        <div key={groupName}>
          <p className="text-[11px] font-semibold text-gray-500 mb-1">{groupName}</p>
          <OptionList
            variations={variations.filter((v) => v.group_name === groupName)}
            selectedIds={selectedIds}
            onSelect={onSelect}
            showAsDelta
          />
        </div>
      ))}
    </div>
  )
}
