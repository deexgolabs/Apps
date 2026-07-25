'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import ImageUploadField from '@/components/ImageUploadField'
import MultiImageUploadField from '@/components/MultiImageUploadField'
import type { ItemVariation, ModuleCategory, ModuleItem } from '@/types'
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
  const [itemGallery, setItemGallery] = useState<string[]>([])
  const [itemFeatured, setItemFeatured] = useState(false)
  const [itemPromoPrice, setItemPromoPrice] = useState('')

  const [variations, setVariations] = useState<ItemVariation[]>([])
  const [variationName, setVariationName] = useState('')
  const [variationPrice, setVariationPrice] = useState('')
  const [variationStock, setVariationStock] = useState('')

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
    setItemGallery([])
    setItemFeatured(false)
    setItemPromoPrice('')
    setVariations([])
    setVariationName('')
    setVariationPrice('')
    setVariationStock('')
  }

  const startEditItem = async (item: ModuleItem) => {
    setEditingId(item.id)
    setItemName(item.name)
    setItemDescription(item.description || '')
    setItemPrice(item.price != null ? String(item.price) : '')
    setItemImageUrl(item.image_url || '')
    setItemCategoryId(item.category_id != null ? String(item.category_id) : '')
    setItemStock(item.stock != null ? String(item.stock) : '')
    setItemData(item.extra?.data || '')
    setItemHora(item.extra?.hora || '')
    setItemGallery(item.extra?.gallery || [])
    setItemFeatured(!!item.extra?.featured)
    setItemPromoPrice(item.extra?.promo_price != null ? String(item.extra.promo_price) : '')
    setVariations(item.variations || [])
  }

  const handleSubmitItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!itemName.trim()) return

    const extra = isAgenda
      ? { data: itemData, hora: itemHora }
      : {
          gallery: itemGallery,
          featured: itemFeatured,
          promo_price: itemPromoPrice.trim() ? parseFloat(itemPromoPrice) : undefined,
        }

    const payload = {
      name: itemName,
      description: itemDescription || null,
      price: isAgenda ? null : itemPrice ? parseFloat(itemPrice) : null,
      image_url: isAgenda ? null : itemImageUrl || null,
      category_id: itemCategoryId ? Number(itemCategoryId) : null,
      stock: isAgenda ? null : itemStock.trim() ? parseInt(itemStock, 10) : null,
      extra,
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

  const handleAddVariation = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingId || !variationName.trim() || !variationPrice.trim()) return
    try {
      const response = await api.post(`${base}/items/${editingId}/variations`, {
        name: variationName,
        price: parseFloat(variationPrice),
        stock: variationStock.trim() ? parseInt(variationStock, 10) : null,
        order: variations.length,
      })
      setVariations([...variations, response.data])
      setVariationName('')
      setVariationPrice('')
      setVariationStock('')
    } catch (error: any) {
      showApiError(error, 'Erro ao criar variação')
    }
  }

  const handleRemoveVariation = async (variationId: number) => {
    if (!editingId) return
    try {
      await api.delete(`${base}/items/${editingId}/variations/${variationId}`)
      setVariations(variations.filter((v) => v.id !== variationId))
    } catch (error) {
      toast.error('Erro ao remover variação')
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
                  placeholder={variations.length > 0 ? 'Preço (ignorado — usa variações)' : 'Preço (opcional)'}
                  disabled={variations.length > 0}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:bg-gray-100"
                />
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={itemStock}
                  onChange={(e) => setItemStock(e.target.value)}
                  placeholder="Estoque (ilimitado)"
                  disabled={variations.length > 0}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:bg-gray-100"
                />
              </div>
              <input
                type="number"
                step="0.01"
                value={itemPromoPrice}
                onChange={(e) => setItemPromoPrice(e.target.value)}
                placeholder="Preço promocional (opcional)"
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={itemFeatured} onChange={(e) => setItemFeatured(e.target.checked)} />
                Item em destaque
              </label>
              <ImageUploadField label="Imagem principal (opcional)" value={itemImageUrl} onChange={setItemImageUrl} />
              <MultiImageUploadField label="Galeria de fotos (opcional)" value={itemGallery} onChange={setItemGallery} />
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

          {editingId && !isAgenda && (
            <div className="border-t border-gray-200 pt-2 mt-2">
              <p className="text-xs font-semibold text-gray-600 mb-1.5">
                Variações (tamanho, sabor, cor...) — quando existem, o preço/estoque acima é ignorado
              </p>
              <div className="space-y-1.5 mb-2">
                {variations.map((v) => (
                  <div key={v.id} className="flex items-center justify-between text-xs border border-gray-200 rounded px-2 py-1">
                    <span>
                      {v.name} · R$ {v.price.toFixed(2)} {v.stock != null && `· estoque: ${v.stock}`}
                    </span>
                    <button type="button" onClick={() => handleRemoveVariation(v.id)} className="text-gray-400 hover:text-red-600">
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                <input
                  type="text"
                  value={variationName}
                  onChange={(e) => setVariationName(e.target.value)}
                  placeholder="Nome"
                  className="px-2 py-1 text-xs border border-gray-300 rounded"
                />
                <input
                  type="number"
                  step="0.01"
                  value={variationPrice}
                  onChange={(e) => setVariationPrice(e.target.value)}
                  placeholder="Preço"
                  className="px-2 py-1 text-xs border border-gray-300 rounded"
                />
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={variationStock}
                  onChange={(e) => setVariationStock(e.target.value)}
                  placeholder="Estoque"
                  className="px-2 py-1 text-xs border border-gray-300 rounded"
                />
              </div>
              <button
                type="button"
                onClick={handleAddVariation}
                className="mt-1.5 text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded hover:bg-gray-200"
              >
                + Adicionar variação
              </button>
            </div>
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
                      {item.extra?.featured && <span className="text-amber-500">★ </span>}
                      {item.name}
                      {item.price != null && (
                        <span className="text-gray-500 font-normal"> · R$ {item.price.toFixed(2)}</span>
                      )}
                      {item.stock != null && (
                        <span className="text-gray-500 font-normal"> · estoque: {item.stock}</span>
                      )}
                      {item.variations?.length > 0 && (
                        <span className="text-gray-500 font-normal"> · {item.variations.length} variação(ões)</span>
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
