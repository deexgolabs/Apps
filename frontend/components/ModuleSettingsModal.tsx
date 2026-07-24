'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import { FIXED_FORM_MODULES, LIST_MODULES, MODULE_FIELDS, ORDER_MODULES, PAYMENT_GATEWAY_MODULES } from '@/lib/moduleFields'
import { ICON_PICKER_OPTIONS } from '@/lib/moduleIcons'
import ItemsManager from '@/components/ItemsManager'
import SubmissionsList from '@/components/SubmissionsList'
import OrdersList from '@/components/OrdersList'
import EndUsersList from '@/components/EndUsersList'
import PushComposer from '@/components/PushComposer'
import ImageUploadField from '@/components/ImageUploadField'
import toast from 'react-hot-toast'

interface ModuleSettingsModalProps {
  appId: string
  moduleName: string
  moduleLabel: string
  onClose: () => void
}

const ICON_SUGGESTIONS = [
  '🍕', '🍔', '☕', '🍰',
  '🛍️', '🛒', '💳',
  '🔧', '💇', '🏋️',
  '📞', '💬', '📍', '🗺️',
  '🎬', '🖼️', '🎵',
  '⭐', '✨', '🎉', '📅',
]

export default function ModuleSettingsModal({
  appId,
  moduleName,
  moduleLabel,
  onClose,
}: ModuleSettingsModalProps) {
  const isListModule = moduleName in LIST_MODULES
  const isOrderModule = ORDER_MODULES.includes(moduleName)
  const isPagamentoEntrega = moduleName === 'pagamento_entrega' || PAYMENT_GATEWAY_MODULES.includes(moduleName)
  const isContatoPersonalizado = moduleName === 'contato_personalizado'
  const isFixedFormModule = !isOrderModule && FIXED_FORM_MODULES.includes(moduleName)
  const isEndUserModule = moduleName === 'login_cadastro'
  const isPushModule = moduleName === 'push_notifications'
  const fields = MODULE_FIELDS[moduleName] || []
  const isMercadoLivre = moduleName === 'mercado_livre'
  const [values, setValues] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [iconTab, setIconTab] = useState<'emoji' | 'vetor'>('emoji')

  // Todo módulo agora busca/salva config — mesmo os que não têm campos próprios
  // (form fixo, login, push) ganham ícone + nome de exibição customizáveis aqui.
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await api.get(`/api/apps/${appId}/module-config/${moduleName}`)
        const settings = response.data.settings || {}
        setValues(settings)
        setIconTab(settings.icon_name ? 'vetor' : 'emoji')
      } catch (error) {
        toast.error('Erro ao carregar configurações do módulo')
      } finally {
        setLoading(false)
      }
    }
    fetchConfig()
  }, [appId, moduleName])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await api.put(`/api/apps/${appId}/module-config/${moduleName}`, { settings: values })
      const response = await api.post(`/api/apps/${appId}/modules/mercado_livre/sync`)
      toast.success(`${response.data.synced} de ${response.data.total} produtos sincronizados!`)
    } catch (error: any) {
      const detail = error.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Erro ao sincronizar com o Mercado Livre')
    } finally {
      setSyncing(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.put(`/api/apps/${appId}/module-config/${moduleName}`, { settings: values })
      toast.success('Configurações salvas!')
      onClose()
    } catch (error: any) {
      const detail = error.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Erro ao salvar configurações')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Configurar: {moduleLabel}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Fechar"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome de exibição</label>
            <input
              type="text"
              value={values.display_name || ''}
              onChange={(e) => setValues({ ...values, display_name: e.target.value })}
              placeholder={moduleLabel}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ícone</label>
            <div className="flex gap-2 mb-2">
              <button
                type="button"
                onClick={() => setIconTab('emoji')}
                className={`flex-1 py-1 text-xs rounded-lg font-medium ${
                  iconTab === 'emoji' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'
                }`}
              >
                Emoji
              </button>
              <button
                type="button"
                onClick={() => setIconTab('vetor')}
                className={`flex-1 py-1 text-xs rounded-lg font-medium ${
                  iconTab === 'vetor' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'
                }`}
              >
                Ícone
              </button>
            </div>

            {iconTab === 'emoji' ? (
              <>
                <input
                  type="text"
                  value={values.icon || ''}
                  onChange={(e) => setValues({ ...values, icon: e.target.value, icon_name: '' })}
                  maxLength={4}
                  placeholder="🍕"
                  className="w-full px-3 py-2 text-xl text-center border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
                <div className="flex flex-wrap gap-1 mt-2">
                  {ICON_SUGGESTIONS.map((emoji) => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => setValues({ ...values, icon: emoji, icon_name: '' })}
                      className="w-8 h-8 flex items-center justify-center text-lg rounded hover:bg-gray-100"
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <div className="grid grid-cols-6 gap-2">
                {ICON_PICKER_OPTIONS.map(({ name, Icon }) => (
                  <button
                    key={name}
                    type="button"
                    onClick={() => setValues({ ...values, icon_name: name, icon: '' })}
                    className={`w-9 h-9 flex items-center justify-center rounded-lg border transition ${
                      values.icon_name === name
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-600'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                    title={name}
                  >
                    <Icon size={18} />
                  </button>
                ))}
              </div>
            )}

            <div className="mt-3">
              <ImageUploadField
                label="Imagem de fundo do ícone (opcional)"
                value={values.icon_background_url || ''}
                onChange={(url) => setValues({ ...values, icon_background_url: url })}
                hint="Recomendado: 400×400px"
              />
            </div>
          </div>

          <hr className="border-gray-200" />

          {isListModule ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Exibição</label>
                <select
                  value={values.layout || 'list'}
                  onChange={(e) => setValues({ ...values, layout: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                >
                  <option value="list">Lista</option>
                  <option value="grid">Grade de cards</option>
                </select>
              </div>

              {isMercadoLivre && (
                <div className="space-y-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Access Token do Mercado Livre</label>
                    <input
                      type="text"
                      value={values.access_token || ''}
                      onChange={(e) => setValues({ ...values, access_token: e.target.value })}
                      placeholder="APP_USR-..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">ID do vendedor (user_id)</label>
                    <input
                      type="text"
                      value={values.user_id || ''}
                      onChange={(e) => setValues({ ...values, user_id: e.target.value })}
                      placeholder="123456789"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSync}
                    disabled={syncing}
                    className="w-full bg-yellow-500 text-white py-2 rounded-lg font-semibold hover:bg-yellow-600 disabled:opacity-50 transition"
                  >
                    {syncing ? 'Sincronizando...' : 'Sincronizar produtos'}
                  </button>
                </div>
              )}

              <ItemsManager appId={appId} moduleName={moduleName} supportsCategories={LIST_MODULES[moduleName]} />
            </>
          ) : isOrderModule ? (
            <OrdersList appId={appId} moduleName={moduleName} />
          ) : isFixedFormModule ? (
            <SubmissionsList appId={appId} moduleName={moduleName} />
          ) : isEndUserModule ? (
            <EndUsersList appId={appId} />
          ) : isPushModule ? (
            <PushComposer appId={appId} />
          ) : loading ? (
            <p className="text-sm text-gray-500">Carregando...</p>
          ) : (
            <>
              {fields.length === 0 ? (
                <p className="text-sm text-gray-500">Este módulo não tem outras configurações.</p>
              ) : (
                fields.map((field) =>
                  field.type === 'image' ? (
                    <ImageUploadField
                      key={field.key}
                      label={field.label}
                      value={values[field.key] || ''}
                      onChange={(url) => setValues({ ...values, [field.key]: url })}
                    />
                  ) : (
                    <div key={field.key}>
                      <label className="block text-sm font-medium text-gray-700 mb-1">{field.label}</label>
                      {field.type === 'textarea' ? (
                        <textarea
                          value={values[field.key] || ''}
                          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
                          placeholder={field.placeholder}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 h-24"
                        />
                      ) : (
                        <input
                          type={field.type === 'url' ? 'url' : 'text'}
                          value={values[field.key] || ''}
                          onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
                          placeholder={field.placeholder}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                        />
                      )}
                    </div>
                  )
                )
              )}
              {isPagamentoEntrega && (
                <>
                  <hr className="border-gray-200" />
                  <OrdersList appId={appId} moduleName={moduleName} />
                </>
              )}
              {isContatoPersonalizado && (
                <>
                  <hr className="border-gray-200" />
                  <SubmissionsList appId={appId} moduleName={moduleName} />
                </>
              )}
            </>
          )}
        </div>

        <div className="flex gap-3 px-6 py-4 border-t border-gray-200">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
            className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg font-semibold hover:bg-gray-50 transition"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
