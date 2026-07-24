'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/store/useAppStore'
import api from '@/lib/api'
import PhoneFrame from '@/components/PhoneFrame'
import ImageUploadField from '@/components/ImageUploadField'
import { MODULE_ICONS } from '@/lib/moduleFields'
import type { Module } from '@/types'
import toast from 'react-hot-toast'

interface Template {
  id: string
  name: string
  icon: string
  inclui: string
  primaryColor: string
  secondaryColor: string
  modules: string[]
}

const TEMPLATES: Template[] = [
  { id: 'restaurant', name: 'Restaurante', icon: '🍽️', inclui: 'Cardápio, WhatsApp, Fale Conosco', primaryColor: '#E11D48', secondaryColor: '#F59E0B', modules: ['cardapio', 'whatsapp', 'fale_conosco', 'mapa', 'calculo_frete'] },
  { id: 'store', name: 'Loja', icon: '🛍️', inclui: 'Catálogo, Frete, Pagamento na entrega', primaryColor: '#4F46E5', secondaryColor: '#10B981', modules: ['catalogo', 'whatsapp', 'calculo_frete', 'fale_conosco', 'pagamento_entrega'] },
  { id: 'service', name: 'Serviço', icon: '🔧', inclui: 'Agenda, WhatsApp, Cotação', primaryColor: '#0EA5E9', secondaryColor: '#6366F1', modules: ['fale_conosco', 'whatsapp', 'agenda_interna', 'mapa', 'cotacao'] },
  { id: 'delivery', name: 'Delivery', icon: '🚚', inclui: 'Cardápio, Pedidos, Frete', primaryColor: '#F97316', secondaryColor: '#22C55E', modules: ['cardapio', 'formulario_delivery', 'calculo_frete', 'whatsapp', 'pagamento_entrega'] },
  { id: 'beauty_salon', name: 'Salão de Beleza', icon: '💇', inclui: 'Agenda, WhatsApp, Galeria', primaryColor: '#DB2777', secondaryColor: '#A855F7', modules: ['agenda_interna', 'whatsapp', 'galeria_imagens', 'fale_conosco', 'mapa'] },
  { id: 'gym', name: 'Academia', icon: '🏋️', inclui: 'Agenda, Fidelidade, WhatsApp', primaryColor: '#111827', secondaryColor: '#F97316', modules: ['agenda_interna', 'cartao_fidelidade', 'whatsapp', 'mapa', 'fale_conosco'] },
  { id: 'pet_shop', name: 'Pet Shop', icon: '🐾', inclui: 'Catálogo, Agenda, Frete', primaryColor: '#0D9488', secondaryColor: '#FBBF24', modules: ['catalogo', 'agenda_interna', 'whatsapp', 'calculo_frete', 'fale_conosco'] },
  { id: 'real_estate', name: 'Imobiliária', icon: '🏠', inclui: 'Galeria, Contato, Mapa', primaryColor: '#1E3A8A', secondaryColor: '#CA8A04', modules: ['galeria_imagens', 'contato_personalizado', 'whatsapp', 'mapa', 'fale_conosco'] },
  { id: 'church_ngo', name: 'Igreja/ONG', icon: '⛪', inclui: 'Agenda, Sobre, WhatsApp', primaryColor: '#1E40AF', secondaryColor: '#EAB308', modules: ['agenda_interna', 'texto', 'whatsapp', 'mapa', 'fale_conosco'] },
  { id: 'education', name: 'Educação/Curso', icon: '🎓', inclui: 'Agenda, Catálogo, Contato', primaryColor: '#4338CA', secondaryColor: '#14B8A6', modules: ['agenda_interna', 'catalogo', 'contato_personalizado', 'fale_conosco', 'whatsapp'] },
  { id: 'other', name: 'Outro', icon: '✨', inclui: 'Texto, Quem Somos, WhatsApp', primaryColor: '#4F46E5', secondaryColor: '#10B981', modules: ['texto', 'quem_somos', 'whatsapp', 'fale_conosco', 'mapa'] },
]

const STEPS = ['Nome', 'Template', 'Marca', 'Preview'] as const

export default function NewAppPage() {
  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [primaryColor, setPrimaryColor] = useState('#4F46E5')
  const [secondaryColor, setSecondaryColor] = useState('#10B981')
  const [logoUrl, setLogoUrl] = useState('')
  const [iconUrl, setIconUrl] = useState('')
  const [modules, setModules] = useState<Module[]>([])
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const addApp = useAppStore((state) => state.addApp)

  useEffect(() => {
    api.get('/api/modules').then((res) => setModules(res.data)).catch(() => {})
  }, [])

  const template = TEMPLATES.find((t) => t.id === templateId)
  const moduleByName = new Map(modules.map((m) => [m.name, m]))

  const selectTemplate = (t: Template) => {
    setTemplateId(t.id)
    setPrimaryColor(t.primaryColor)
    setSecondaryColor(t.secondaryColor)
  }

  const canAdvance = () => {
    if (step === 0) return name.trim().length > 0
    if (step === 1) return !!templateId
    return true
  }

  const handleNext = () => {
    if (!canAdvance()) {
      toast.error(step === 0 ? 'Digite um nome para o app' : 'Selecione um template')
      return
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1))
  }

  const handleCreate = async () => {
    setLoading(true)
    try {
      const response = await api.post('/api/apps', {
        name,
        description,
        template_type: templateId,
        config: {
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          logo_url: logoUrl,
          icon_url: iconUrl,
        },
      })

      addApp(response.data)
      toast.success('Aplicativo criado com sucesso!')
      router.push(`/dashboard/apps/${response.data.id}`)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao criar aplicativo')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="py-12 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Criar Novo Aplicativo</h1>

        <div className="flex items-center gap-2 mb-8 mt-6">
          {STEPS.map((label, idx) => (
            <div key={label} className="flex items-center gap-2 flex-1">
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
                    idx <= step ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {idx + 1}
                </div>
                <span className={`text-sm ${idx === step ? 'font-semibold text-gray-900' : 'text-gray-500'}`}>
                  {label}
                </span>
              </div>
              {idx < STEPS.length - 1 && <div className="flex-1 h-px bg-gray-200" />}
            </div>
          ))}
        </div>

        {step === 0 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nome do Aplicativo</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                placeholder="Meu App Incrível"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Descrição</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 h-24"
                placeholder="Descreva seu aplicativo"
              />
            </div>
          </div>
        )}

        {step === 1 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-4">Escolha um Template</label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => selectTemplate(t)}
                  className={`p-4 rounded-lg border-2 transition text-center ${
                    templateId === t.id ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:border-indigo-400'
                  }`}
                >
                  <div
                    className="w-12 h-12 mx-auto mb-2 rounded-full flex items-center justify-center text-2xl"
                    style={{ backgroundColor: `${t.primaryColor}1A` }}
                  >
                    {t.icon}
                  </div>
                  <div className="font-medium text-sm text-gray-900">{t.name}</div>
                  <div className="text-xs text-gray-500 mt-1">{t.inclui}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Cor Primária</label>
                <input
                  type="color"
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  className="w-full h-10 border border-gray-300 rounded-lg cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Cor Secundária</label>
                <input
                  type="color"
                  value={secondaryColor}
                  onChange={(e) => setSecondaryColor(e.target.value)}
                  className="w-full h-10 border border-gray-300 rounded-lg cursor-pointer"
                />
              </div>
            </div>
            <ImageUploadField label="Logo (opcional)" value={logoUrl} onChange={setLogoUrl} />
            <ImageUploadField label="Ícone do app (opcional)" value={iconUrl} onChange={setIconUrl} />
          </div>
        )}

        {step === 3 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-4 text-center">Confira como seu app vai ficar</p>
            <PhoneFrame>
              <div className="h-10 flex items-center justify-between px-3 shrink-0" style={{ backgroundColor: primaryColor }}>
                <span className="text-white text-lg leading-none">☰</span>
                {logoUrl ? (
                  <img src={logoUrl} alt={name} className="h-6 object-contain" />
                ) : (
                  <span className="text-white text-sm font-semibold truncate">{name || 'Meu App'}</span>
                )}
                <span className="w-4" />
              </div>
              <div className="p-4" style={{ borderTop: `2px solid ${secondaryColor}` }}>
                <p className="text-xs text-gray-400 mb-3">Módulos incluídos no template "{template?.name}":</p>
                <div className="space-y-2">
                  {(template?.modules || []).map((name) => (
                    <div key={name} className="text-sm text-gray-700 border-b border-gray-100 pb-2">
                      {MODULE_ICONS[name] || '📦'} {moduleByName.get(name)?.description || name}
                    </div>
                  ))}
                </div>
              </div>
            </PhoneFrame>
          </div>
        )}

        <div className="flex gap-4 pt-8 mt-8 border-t border-gray-200">
          {step > 0 && (
            <button
              type="button"
              onClick={() => setStep((s) => s - 1)}
              className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg font-semibold hover:bg-gray-50 transition"
            >
              Voltar
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={handleNext}
              className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 transition"
            >
              Avançar
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCreate}
              disabled={loading}
              className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {loading ? 'Criando...' : 'Criar Aplicativo'}
            </button>
          )}
          {step === 0 && (
            <button
              type="button"
              onClick={() => router.back()}
              className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg font-semibold hover:bg-gray-50 transition"
            >
              Cancelar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
