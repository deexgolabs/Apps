'use client'

export default function WishlistButton({
  favorited,
  onToggle,
}: {
  favorited: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        onToggle()
      }}
      aria-label={favorited ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
      className={`shrink-0 text-base leading-none ${favorited ? 'text-red-500' : 'text-gray-300 hover:text-gray-400'}`}
    >
      {favorited ? '♥' : '♡'}
    </button>
  )
}
