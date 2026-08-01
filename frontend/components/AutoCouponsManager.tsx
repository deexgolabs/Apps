'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { showApiError } from '@/lib/apiError'

interface AutoCouponRule {
  id: number
  trigger: 'birthday' | 'first_purchase' | 'referral'
  discount_type: 'percent' | 'fixed'
  discount_value: number
  valid_days: number
  active: boolean
}

const TRIGGER_LABELS: Record<string, string> = {
  birthday: '🎂 Aniversário do cliente',
  first_purchase: '🎉 Depois da primeira compra',
  referral: '🤝 Indicação de amigo',
}

const TRIGGERS: AutoCouponRule['trigger'][] = ['birthday', 'first_purchase', 'referral']

type DraftRule = { discount_type: 'percent' | 'fixed'; discount_value: string; valid_days: string; active: boolean }

const emptyDraft = (): DraftRule => ({ discount_type: 'percent', discount_value: '', valid_days: '30', active: true })

export default function AutoCouponsManager({ appId }: { appId: string }) {
  const [rules, setRules] = useState<Record<string, AutoCouponRule>>({})
  const [drafts, setDrafts] = useState<Record<string, DraftRule>>({})
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)

  const fetchRules = async () => {
    try {
      const res = await api.get<AutoCouponRule[]>(`/api/apps/${appId}/auto-coupons`)
      const byTrigger: Record<string, AutoCouponRule> = {}
      const draftsByTrigger: Record<string, DraftRule> = {}
      for (const t of TRIGGERS) draftsByTrigger[t] = emptyDraft()
      for (const rule of res.data) {
        byTrigger[rule.trigger] = rule
        draftsByTrigger[rule.trigger] = {
          discount_type: rule.discount_type,
          discount_value: String(rule.discount_value),
          valid_days: String(rule.valid_days),
          active: rule.active,
        }
      }
      setRules(byTrigger)
      setDrafts(draftsByTrigger)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRules()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId])

  const updateDraft = (trigger: string, patch: Partial<DraftRule>) => {
    setDrafts((prev) => ({ ...prev, [trigger]: { ...(prev[trigger] || emptyDraft()), ...patch } }))
  }

  const handleSave = async (trigger: string) => {
    const draft = drafts[trigger] || emptyDraft()
    if (!draft.discount_value.trim()) {
      toast.error('Informe o valor do desconto')
      return
    }
    setSaving(trigger)
    try {
      const res = await api.put(`/api/apps/${appId}/auto-coupons/${trigger}`, {
        discount_type: draft.discount_type,
        discount_value: parseFloat(draft.discount_value),
        valid_days: parseInt(draft.valid_days, 10) || 30,
        active: draft.active,
      })
      setRules((prev) => ({ ...prev, [trigger]: res.data }))
      toast.success('Regra salva!')
    } catch (error: any) {
      showApiError(error, 'Erro ao salvar regra')
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700"
      >
        <span>Cupons automáticos</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-3 border-t border-gray-200 space-y-3">
          <p className="text-xs text-gray-500">
            Gera um cupom pessoal e único pro cliente automaticamente, sem precisar criar nada na mão.
          </p>
          {loading ? (
            <p className="text-sm text-gray-500">Carregando...</p>
          ) : (
            TRIGGERS.map((trigger) => {
              const draft = drafts[trigger] || emptyDraft()
              const rule = rules[trigger]
              return (
                <div key={trigger} className="border border-gray-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-800">{TRIGGER_LABELS[trigger]}</p>
                    <button
                      type="button"
                      onClick={() => updateDraft(trigger, { active: !draft.active })}
                      className={`text-xs px-2 py-1 rounded ${
                        draft.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {draft.active ? 'Ativo' : 'Inativo'}
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <select
                      value={draft.discount_type}
                      onChange={(e) => updateDraft(trigger, { discount_type: e.target.value as 'percent' | 'fixed' })}
                      className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                    >
                      <option value="percent">Percentual (%)</option>
                      <option value="fixed">Valor fixo (R$)</option>
                    </select>
                    <input
                      type="number"
                      step="0.01"
                      value={draft.discount_value}
                      onChange={(e) => updateDraft(trigger, { discount_value: e.target.value })}
                      placeholder={draft.discount_type === 'percent' ? 'Ex: 10' : 'Ex: 15.00'}
                      className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                    />
                    <input
                      type="number"
                      step="1"
                      value={draft.valid_days}
                      onChange={(e) => updateDraft(trigger, { valid_days: e.target.value })}
                      placeholder="Validade (dias)"
                      className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleSave(trigger)}
                    disabled={saving === trigger}
                    className="w-full bg-indigo-600 text-white py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {saving === trigger ? 'Salvando...' : rule ? 'Atualizar regra' : 'Ativar'}
                  </button>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
