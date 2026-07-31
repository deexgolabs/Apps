'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

interface Coupon {
  id: number
  code: string
  discount_type: 'percent' | 'fixed'
  discount_value: number
  min_order_value: number | null
  max_uses: number | null
  uses_count: number
  active: boolean
}

export default function CouponsManager({ appId }: { appId: string }) {
  const [coupons, setCoupons] = useState<Coupon[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  const [code, setCode] = useState('')
  const [discountType, setDiscountType] = useState<'percent' | 'fixed'>('percent')
  const [discountValue, setDiscountValue] = useState('')
  const [minOrderValue, setMinOrderValue] = useState('')
  const [maxUses, setMaxUses] = useState('')

  const fetchCoupons = async () => {
    try {
      const res = await api.get<Coupon[]>(`/api/apps/${appId}/coupons`)
      setCoupons(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCoupons()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const handleCreate = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!code.trim() || !discountValue.trim()) return
    try {
      const res = await api.post(`/api/apps/${appId}/coupons`, {
        code,
        discount_type: discountType,
        discount_value: parseFloat(discountValue),
        min_order_value: minOrderValue.trim() ? parseFloat(minOrderValue) : null,
        max_uses: maxUses.trim() ? parseInt(maxUses, 10) : null,
      })
      setCoupons([res.data, ...coupons])
      setCode('')
      setDiscountValue('')
      setMinOrderValue('')
      setMaxUses('')
      toast.success('Cupom criado!')
    } catch (error: any) {
      showApiError(error, 'Erro ao criar cupom')
    }
  }

  const handleToggleActive = async (coupon: Coupon) => {
    try {
      const res = await api.put(`/api/apps/${appId}/coupons/${coupon.id}`, { active: !coupon.active })
      setCoupons(coupons.map((c) => (c.id === coupon.id ? res.data : c)))
    } catch {
      toast.error('Erro ao atualizar cupom')
    }
  }

  const handleDelete = async (couponId: number) => {
    try {
      await api.delete(`/api/apps/${appId}/coupons/${couponId}`)
      setCoupons(coupons.filter((c) => c.id !== couponId))
    } catch {
      toast.error('Erro ao remover cupom')
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700"
      >
        <span>Cupons de desconto {coupons.length > 0 && `(${coupons.length})`}</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-3 border-t border-gray-200 space-y-3">
          {loading ? (
            <p className="text-sm text-gray-500">Carregando...</p>
          ) : (
            <>
              {/* Não usa <form> aqui de propósito: este painel renderiza dentro do
                  <form> maior da página (aba "Pedidos" faz parte do form de salvar
                  o app inteiro) — um <form> aninhado faz o clique disparar o submit
                  do form de fora em vez deste, então o botão é type="button" + onClick. */}
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="Código (ex: PROMO10)"
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                  />
                  <select
                    value={discountType}
                    onChange={(e) => setDiscountType(e.target.value as 'percent' | 'fixed')}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                  >
                    <option value="percent">Percentual (%)</option>
                    <option value="fixed">Valor fixo (R$)</option>
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="number"
                    step="0.01"
                    value={discountValue}
                    onChange={(e) => setDiscountValue(e.target.value)}
                    placeholder={discountType === 'percent' ? 'Ex: 10' : 'Ex: 15.00'}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                  />
                  <input
                    type="number"
                    step="0.01"
                    value={minOrderValue}
                    onChange={(e) => setMinOrderValue(e.target.value)}
                    placeholder="Pedido mínimo"
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                  />
                  <input
                    type="number"
                    step="1"
                    value={maxUses}
                    onChange={(e) => setMaxUses(e.target.value)}
                    placeholder="Usos máx."
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleCreate()}
                  className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700"
                >
                  + Criar cupom
                </button>
              </div>

              <div className="space-y-1.5">
                {coupons.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">Nenhum cupom criado ainda</p>
                ) : (
                  coupons.map((c) => (
                    <div
                      key={c.id}
                      className="flex items-center justify-between gap-2 border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900">
                          {c.code}{' '}
                          <span className="text-gray-500 font-normal">
                            {c.discount_type === 'percent' ? `${c.discount_value}%` : `R$ ${c.discount_value.toFixed(2)}`}
                          </span>
                        </p>
                        <p className="text-xs text-gray-500">
                          {c.uses_count} uso(s){c.max_uses ? ` de ${c.max_uses}` : ''}
                          {c.min_order_value ? ` · mín. R$ ${c.min_order_value.toFixed(2)}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          type="button"
                          onClick={() => handleToggleActive(c)}
                          className={`text-xs px-2 py-1 rounded ${
                            c.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                          }`}
                        >
                          {c.active ? 'Ativo' : 'Inativo'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(c.id)}
                          className="text-gray-400 hover:text-red-600"
                          aria-label={`Remover cupom ${c.code}`}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
