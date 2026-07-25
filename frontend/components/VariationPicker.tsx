'use client'

import type { ItemVariation } from '@/types'

export default function VariationPicker({
  variations,
  selectedId,
  onSelect,
}: {
  variations: ItemVariation[]
  selectedId: number | null
  onSelect: (variation: ItemVariation) => void
}) {
  return (
    <div className="space-y-1.5">
      {variations.map((v) => {
        const outOfStock = v.stock !== null && v.stock <= 0
        return (
          <label
            key={v.id}
            className={`flex items-center justify-between gap-2 border rounded px-2 py-1.5 text-xs cursor-pointer ${
              selectedId === v.id ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'
            } ${outOfStock ? 'opacity-40 pointer-events-none' : ''}`}
          >
            <span className="flex items-center gap-1.5">
              <input
                type="radio"
                checked={selectedId === v.id}
                onChange={() => onSelect(v)}
                disabled={outOfStock}
              />
              {v.name}
            </span>
            <span className="text-gray-600">{outOfStock ? 'Esgotado' : `R$ ${v.price.toFixed(2)}`}</span>
          </label>
        )
      })}
    </div>
  )
}
