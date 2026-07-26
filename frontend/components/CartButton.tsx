'use client'

import { useCart } from '@/context/CartContext'

export default function CartButton({
  onClick,
  color,
  raised = false,
}: {
  onClick: () => void
  color: string
  /** true quando a BottomTabBar está ativa, pra não ficar coberto por ela. */
  raised?: boolean
}) {
  const { count } = useCart()
  if (count === 0) return null

  return (
    <button
      type="button"
      onClick={onClick}
      className={`absolute ${raised ? 'bottom-20' : 'bottom-4'} right-4 z-20 flex items-center gap-1.5 rounded-full px-4 py-2 text-white text-sm font-semibold shadow-lg`}
      style={{ backgroundColor: color }}
    >
      🛒 <span>{count}</span>
    </button>
  )
}
