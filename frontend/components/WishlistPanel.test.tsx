import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import WishlistPanel from './WishlistPanel'

describe('WishlistPanel', () => {
  it('calls onToggle when clicked', () => {
    const onToggle = vi.fn()
    render(<WishlistPanel active={false} onToggle={onToggle} />)

    fireEvent.click(screen.getByRole('button', { name: /Favoritos/ }))

    expect(onToggle).toHaveBeenCalledOnce()
  })

  it('reflects the active state visually', () => {
    const { rerender } = render(<WishlistPanel active={false} onToggle={() => {}} />)
    const button = screen.getByRole('button', { name: /Favoritos/ })
    expect(button.className).not.toMatch(/bg-red-50/)

    rerender(<WishlistPanel active={true} onToggle={() => {}} />)
    expect(button.className).toMatch(/bg-red-50/)
  })
})
