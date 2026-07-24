'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import ImageUploadField from '@/components/ImageUploadField'
import type { ModuleCategory, ModuleItem } from '@/types'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

interface ItemsManagerProps {
  appId: string
  moduleName: string
  supportsCategories: boolean
}

export default function ItemsManager({ appId, moduleName, supportsCategories }: ItemsManagerProps) {
  const isAgenda = moduleName === 'agenda_interna'
  const [categories, setCategories] = useState<ModuleCategory[]>([])
  const [items, setItems] = useState<ModuleItem[]>([])
  const [loading, setLoading] = useState(true)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [itemName, setItemName] = useState('')
  const [itemDescription, setItemDescription] = useState('')
  const [itemPrice, setItemPrice] = useState('')
  const [itemImageUrl, setItemImageUrl] = useState('')
  const [itemCategoryId, setItemCategoryId] = useState('')
  const [itemStock, setItemStock] = useState('')
  const [itemData, setItemData] = useState('')
  const [itemHora, setItemHora] = useState('')

  const base = `/api/apps/${appId}/modules/${moduleName}`

  const fetchAll = async () => {
    try {
      const itemsPromise = api.get<ModuleItem[]>(`${base}/items`)
      const categoriesPromise = supportsCategories
        ? api.get<ModuleCategory[]>(`${base}/categories`)
        : Promise.resolve(null)

      const [itemsRes, categoriesRes] = await Promise.all([itemsPromise, categoriesPromise])
      setItems(itemsRes.data)
      if (categoriesRes) setCategories(categoriesRes.data)
    } catch (error) {
      toast.error('Erro ao carregar itens')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId, moduleName])

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCategoryName.trim()) return

    try {
      const response = await api.post(`${base}/categories`, { name: newCategoryName, order: categories.length })
      setCategories([...categories, response.data])
      setNewCategoryName('')
    } catch (error: any) {
      showApiError(error, 'Erro ao criar categoria')
    }
  }

  const handleRemoveCategory = async (categoryId: number) => {
    try {
      await api.delete(`${base}/categories/${categoryId}`)
      setCategories(categories.filter((c) => c.id !== categoryId))
      setItems(items.map((i) => (i.category_id === categoryId ? { ...i, category_id: null } : i)))
    } catch (error) {
      toast.error('Erro ao remover categoria')
    }
  }

  const resetItemForm = () => {
    setEditingId(null)
    setItemName('')
    setItemDescription('')
    setItemPrice('')
    setItemImageUrl('')
    setItemCategoryId('')
    setItemStock('')
    setItemData('')
    setItemHora('')
  }

  const startEditItem = (item: ModuleItem) => {
    setEditingId(item.id)
    setItemName(item.name)
    setItemDescription(item.description || '')
    setItemPrice(item.price != null ? String(item.price) : '')
    setItemImageUrl(item.image_url || '')
    setItemCategoryId(item.category_id != null ? String(item.category_id) : '')
    setItemStock(item.stock != null ? String(item.stock) : '')
    setItemData(item.extra?.data || '')
    setItemHora(item.extra?.hora || '')
  }

  const handleSubmitItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!itemName.trim()) return

    const payload = {
      name: itemName,
      description: itemDescription || null,
      price: isAgenda ? null : itemPrice ? parseFloat(itemPrice) : null,
      image_url: isAgenda ? null : itemImageUrl || null,
      category_id: itemCategoryId ? Number(itemCategoryId) : null,
      stock: isAgenda ? null : itemStock.trim() ? parseInt(itemStock, 10) : null,
      extra: isAgenda ? { data: itemData, hora: itemHora } : {},
    }

    try {
      if (editingId) {
        const response = await api.put(`${base}/items/${editingId}`, payload)
        setItems(items.map((i) => (i.id === editingId ? response.data : i)))
        toast.success('Item atualizado!')
      } else {
        const response = await api.post(`${base}/items`, { ...payload, order: items.length })
        setItems([...items, response.data])
        toast.success('Item adicionado!')
      }
      resetItemForm()
    } catch (error: any) {
      showApiError(error, editingId ? 'Erro ao atualizar item' : 'Erro ao criar item')
    }
  }

  const handleRemoveItem = async (itemId: number) => {
    try {
      await api.delete(`${base}/items/${itemId}`)
      setItems(items.filter((i) => i.id !== itemId))
      if (editingId === itemId) resetItemForm()
    } catch (error) {
      toast.error('Erro ao remover item')
    }
  }

  const categoryName = (categoryId: number | null) =>
    categories.find((c) => c.id === categoryId)?.name

  if (loading) {
    return <p className="text-sm text-gray-500">Carregando...</p>
  }

  return (
    <div className="space-y-6">
      {supportsCategories && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Categorias</p>
          <form onSubmit={handleAddCategory} className="flex gap-2 mb-3">
            <input
              type="text"
              value={newCategoryName}
              onChange={(e) => setNewCategoryName(e.target.value)}
              placeholder="Nova categoria"
              className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <button
              type="submit"
              className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Adicionar
            </button>
          </form>
          <div className="flex flex-wrap gap-2">
            {categories.map((c) => (
              <span
                key={c.id}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
              >
                {c.name}
                <button
                  type="button"
                  onClick={() => handleRemoveCategory(c.id)}
                  className="text-gray-400 hover:text-red-600"
                  aria-label={`Remover categoria ${c.name}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">{editingId ? 'Editar item' : 'Novo item'}</p>
        <form onSubmit={handleSubmitItem} className="space-y-2 border border-gray-200 rounded-lg p-3">
          <input
            type="text"
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
            placeholder="Nome"
            required
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
          <textarea
            value={itemDescription}
            onChange={(e) => setItemDescription(e.target.value)}
            placeholder="Descrição (opcional)"
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
          {isAgenda ? (
            <div className="grid grid-cols-2 gap-2">
              <input
                type="date"
                value={itemData}
                onChange={(e) => setItemData(e.target.value)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
              <input
                type="time"
                value={itemHora}
                onChange={(e) => setItemHora(e.target.value)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.01"
                  value={itemPrice}
                  onChange={(e) => setItemPrice(e.target.value)}
                  placeholder="Preço (opcional)"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={itemStock}
                  onChange={(e) => setItemStock(e.target.value)}
                  placeholder="Estoque (ilimitado)"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <ImageUploadField label="Imagem (opcional)" value={itemImageUrl} onChange={setItemImageUrl} />
            </>
          )}
          {supportsCategories && categories.length > 0 && (
            <select
              value={itemCategoryId}
              onChange={(e) => setItemCategoryId(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            >
              <option value="">Sem categoria</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition"
            >
              {editingId ? 'Salvar alterações' : '+ Adicionar item'}
            </button>
            {editingId && (
              <button
                type="button"
                onClick={resetItemForm}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50"
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Itens ({items.length})</p>
        <div className="space-y-2">
          {items.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Nenhum item ainda</p>
          ) : (
            items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between gap-2 border border-gray-200 rounded-lg px-3 py-2"
              >
                <button
                  type="button"
                  onClick={() => startEditItem(item)}
                  className="flex items-center gap-2 min-w-0 flex-1 text-left"
                >
                  {item.image_url && (
                    <img src={item.image_url} alt="" className="w-8 h-8 object-cover rounded flex-shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.name}
                      {item.price != null && (
                        <span className="text-gray-500 font-normal"> · R$ {item.price.toFixed(2)}</span>
                      )}
                      {item.stock != null && (
                        <span className="text-gray-500 font-normal"> · estoque: {item.stock}</span>
                      )}
                      {isAgenda && (item.extra?.data || item.extra?.hora) && (
                        <span className="text-gray-500 font-normal">
                          {' '}
                          · {item.extra?.data} {item.extra?.hora}
                        </span>
                      )}
                    </p>
                    {(item.description || categoryName(item.category_id)) && (
                      <p className="text-xs text-gray-500 truncate">
                        {categoryName(item.category_id) && `${categoryName(item.category_id)} · `}
                        {item.description}
                      </p>
                    )}
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => handleRemoveItem(item.id)}
                  className="text-gray-400 hover:text-red-600 text-sm leading-none px-1 flex-shrink-0"
                  aria-label={`Remover ${item.name}`}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
