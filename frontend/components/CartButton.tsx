'use client'

import { useCart } from '@/context/CartContext'

export default function CartButton({ onClick, color }: { onClick: () => void; color: string }) {
  const { count } = useCart()
  if (count === 0) return null

  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute bottom-4 right-4 z-20 flex items-center gap-1.5 rounded-full px-4 py-2 text-white text-sm font-semibold shadow-lg"
      style={{ backgroundColor: color }}
    >
      🛒 <span>{count}</span>
    </button>
  )
}
