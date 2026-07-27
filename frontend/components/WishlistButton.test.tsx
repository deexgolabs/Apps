import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import WishlistButton from './WishlistButton'

describe('WishlistButton', () => {
  it('renders a hollow heart when not favorited', () => {
    render(<WishlistButton favorited={false} onToggle={() => {}} />)
    expect(screen.getByRole('button', { name: 'Adicionar aos favoritos' })).toHaveTextContent('♡')
  })

  it('renders a filled heart when favorited', () => {
    render(<WishlistButton favorited={true} onToggle={() => {}} />)
    expect(screen.getByRole('button', { name: 'Remover dos favoritos' })).toHaveTextContent('♥')
  })

  it('calls onToggle and stops the click from bubbling (so it does not trigger a parent card click)', () => {
    const onToggle = vi.fn()
    const onParentClick = vi.fn()
    render(
      <div onClick={onParentClick}>
        <WishlistButton favorited={false} onToggle={onToggle} />
      </div>
    )

    fireEvent.click(screen.getByRole('button'))

    expect(onToggle).toHaveBeenCalledOnce()
    expect(onParentClick).not.toHaveBeenCalled()
  })
})
