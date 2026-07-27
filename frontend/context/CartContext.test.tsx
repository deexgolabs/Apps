import type { ReactNode } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CartProvider, useCart } from './CartContext'
import { publicApi } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  publicApi: { get: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

function wrapper({ children }: { children: ReactNode }) {
  return <CartProvider appId="1">{children}</CartProvider>
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('CartContext', () => {
  it('starts empty', () => {
    const { result } = renderHook(() => useCart(), { wrapper })
    expect(result.current.items).toEqual([])
    expect(result.current.subtotal).toBe(0)
    expect(result.current.count).toBe(0)
    expect(result.current.cartModuleName).toBeNull()
  })

  it('adds a new item to the cart', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0]).toMatchObject({ item_id: 1, name: 'Pizza', unit_price: 30, quantity: 1 })
    expect(result.current.subtotal).toBe(30)
    expect(result.current.count).toBe(1)
    expect(result.current.cartModuleName).toBe('cardapio')
  })

  it('increments quantity when the same item/variation combo is added again', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0].quantity).toBe(2)
    expect(result.current.subtotal).toBe(60)
  })

  it('treats different variation_ids as separate cart lines for the same item', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', {
        id: 1,
        name: 'Pizza (P)',
        price: 20,
        image_url: null,
        stock: null,
        variation_ids: [10],
      })
      result.current.addItem('cardapio', {
        id: 1,
        name: 'Pizza (G)',
        price: 35,
        image_url: null,
        stock: null,
        variation_ids: [11],
      })
    })

    expect(result.current.items).toHaveLength(2)
    expect(result.current.subtotal).toBe(55)
  })

  it('ignores variation_ids order when matching an existing line (combo identity)', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', {
        id: 1,
        name: 'Combo',
        price: 40,
        image_url: null,
        stock: null,
        variation_ids: [2, 1],
      })
      result.current.addItem('cardapio', {
        id: 1,
        name: 'Combo',
        price: 40,
        image_url: null,
        stock: null,
        variation_ids: [1, 2],
      })
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0].quantity).toBe(2)
  })

  it('refuses to add an item from a different module than what is already in the cart', async () => {
    const toast = (await import('react-hot-toast')).default
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })
    act(() => {
      result.current.addItem('catalogo', { id: 2, name: 'Camiseta', price: 50, image_url: null, stock: null })
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0].name).toBe('Pizza')
    expect(toast.error).toHaveBeenCalled()
  })

  it('setQuantity updates the quantity of the matching line', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })
    act(() => {
      result.current.setQuantity(1, 5)
    })

    expect(result.current.items[0].quantity).toBe(5)
    expect(result.current.subtotal).toBe(150)
  })

  it('setQuantity below 1 removes the line entirely', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })
    act(() => {
      result.current.setQuantity(1, 0)
    })

    expect(result.current.items).toEqual([])
  })

  it('removeItem removes only the matching item/variation line', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
      result.current.addItem('cardapio', { id: 2, name: 'Refri', price: 6, image_url: null, stock: null })
    })
    act(() => {
      result.current.removeItem(1)
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0].item_id).toBe(2)
  })

  it('clear empties the cart', () => {
    const { result } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })
    act(() => {
      result.current.clear()
    })

    expect(result.current.items).toEqual([])
    expect(result.current.cartModuleName).toBeNull()
  })

  it('persists the cart to localStorage per appId and restores it on mount', () => {
    const { result, unmount } = renderHook(() => useCart(), { wrapper })

    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })
    unmount()

    expect(JSON.parse(localStorage.getItem('cart_1')!)).toHaveLength(1)

    const { result: result2 } = renderHook(() => useCart(), { wrapper })
    expect(result2.current.items).toHaveLength(1)
    expect(result2.current.items[0].name).toBe('Pizza')
  })

  it('restoreFromOrder rebuilds the cart from current item/variation data, skipping items that no longer exist', async () => {
    vi.mocked(publicApi.get).mockResolvedValue({
      data: [
        {
          id: 1,
          name: 'Pizza',
          price: 30,
          image_url: null,
          stock: 10,
          variations: [{ id: 5, item_id: 1, name: 'Grande', price: 45, stock: 3, order: 0, group_name: null }],
        },
      ],
    })

    const { result } = renderHook(() => useCart(), { wrapper })

    await act(async () => {
      await result.current.restoreFromOrder(
        [
          { id: 1, module_item_id: 1, item_variation_id: 5, name: 'Pizza (Grande)', unit_price: 45, quantity: 2, subtotal: 90 },
          { id: 2, module_item_id: 999, item_variation_id: null, name: 'Item removido', unit_price: 10, quantity: 1, subtotal: 10 },
        ],
        'cardapio'
      )
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0]).toMatchObject({ item_id: 1, name: 'Pizza (Grande)', unit_price: 45, quantity: 2 })
  })

  it('restoreFromOrder leaves the cart untouched if the request fails', async () => {
    vi.mocked(publicApi.get).mockRejectedValue(new Error('network error'))

    const { result } = renderHook(() => useCart(), { wrapper })
    act(() => {
      result.current.addItem('cardapio', { id: 1, name: 'Pizza', price: 30, image_url: null, stock: null })
    })

    await act(async () => {
      await result.current.restoreFromOrder([], 'cardapio')
    })

    await waitFor(() => expect(result.current.items).toHaveLength(1))
  })
})
