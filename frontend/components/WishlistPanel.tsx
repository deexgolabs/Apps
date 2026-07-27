'use client'

export default function WishlistPanel({
  active,
  onToggle,
}: {
  active: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`text-sm border rounded px-2 py-1.5 whitespace-nowrap ${
        active ? 'bg-red-50 border-red-300 text-red-600' : 'border-gray-300 text-gray-600'
      }`}
    >
      ♥ Favoritos
    </button>
  )
}
