'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import toast from 'react-hot-toast'
import { publicApi } from '@/lib/api'
import type { OrderItem } from '@/types'

export interface CartItem {
  item_id: number
  module_name: string
  name: string
  unit_price: number
  quantity: number
  image_url: string | null
  stock: number | null
}

interface CartContextValue {
  items: CartItem[]
  addItem: (
    moduleName: string,
    item: { id: number; name: string; price: number | null; image_url: string | null; stock: number | null }
  ) => void
  removeItem: (itemId: number) => void
  setQuantity: (itemId: number, quantity: number) => void
  clear: () => void
  subtotal: number
  count: number
  /** Nome do módulo dos itens no carrinho — null se o carrinho estiver vazio. */
  cartModuleName: string | null
  restoreFromOrder: (orderItems: OrderItem[], moduleName: string) => Promise<void>
}

const CartContext = createContext<CartContextValue | null>(null)

function storageKey(appId: string) {
  return `cart_${appId}`
}

export function CartProvider({ appId, children }: { appId: string; children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey(appId))
      if (raw) setItems(JSON.parse(raw))
    } catch {
      // ignora carrinho corrompido
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  useEffect(() => {
    localStorage.setItem(storageKey(appId), JSON.stringify(items))
  }, [appId, items])

  const addItem: CartContextValue['addItem'] = (moduleName, item) => {
    setItems((prev) => {
      if (prev.length > 0 && prev[0].module_name !== moduleName) {
        toast.error('Finalize ou limpe o carrinho atual antes de adicionar itens de outro módulo.')
        return prev
      }
      const existing = prev.find((i) => i.item_id === item.id)
      if (existing) {
        return prev.map((i) => (i.item_id === item.id ? { ...i, quantity: i.quantity + 1 } : i))
      }
      return [
        ...prev,
        {
          item_id: item.id,
          module_name: moduleName,
          name: item.name,
          unit_price: item.price || 0,
          quantity: 1,
          image_url: item.image_url,
          stock: item.stock,
        },
      ]
    })
  }

  const removeItem = (itemId: number) => {
    setItems((prev) => prev.filter((i) => i.item_id !== itemId))
  }

  const setQuantity = (itemId: number, quantity: number) => {
    if (quantity < 1) {
      removeItem(itemId)
      return
    }
    setItems((prev) => prev.map((i) => (i.item_id === itemId ? { ...i, quantity } : i)))
  }

  const clear = () => setItems([])

  const restoreFromOrder: CartContextValue['restoreFromOrder'] = async (orderItems, moduleName) => {
    try {
      const res = await publicApi.get(`/api/apps/${appId}/public/modules/${moduleName}/items`)
      const currentItems: { id: number; name: string; price: number | null; image_url: string | null; stock: number | null }[] = res.data
      const currentById = new Map(currentItems.map((i) => [i.id, i]))
      const restored: CartItem[] = []
      for (const oi of orderItems) {
        if (oi.module_item_id == null) continue
        const current = currentById.get(oi.module_item_id)
        if (!current) continue
        restored.push({
          item_id: current.id,
          module_name: moduleName,
          name: current.name,
          unit_price: current.price || 0,
          quantity: oi.quantity,
          image_url: current.image_url,
          stock: current.stock,
        })
      }
      setItems(restored)
    } catch {
      // se a consulta falhar, não mexe no carrinho atual
    }
  }

  const subtotal = items.reduce((sum, i) => sum + i.unit_price * i.quantity, 0)
  const count = items.reduce((sum, i) => sum + i.quantity, 0)
  const cartModuleName = items[0]?.module_name ?? null

  return (
    <CartContext.Provider
      value={{ items, addItem, removeItem, setQuantity, clear, subtotal, count, cartModuleName, restoreFromOrder }}
    >
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart deve ser usado dentro de um CartProvider')
  return ctx
}

/** Como useCart(), mas retorna null em vez de lançar erro quando não há
 * CartProvider por perto — usado por componentes que renderizam tanto no
 * modo owner (sem carrinho) quanto no modo public (com carrinho). */
export function useOptionalCart() {
  return useContext(CartContext)
}
