'use client'

import { useEffect, useState } from 'react'

export interface TourStep {
  selector: string
  title: string
  text: string
}

interface GuidedTourProps {
  storageKey: string
  steps: TourStep[]
  onStepChange?: (index: number) => void
}

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

function getRect(selector: string): Rect | null {
  const el = document.querySelector(selector)
  if (!el) return null
  const r = el.getBoundingClientRect()
  return { top: r.top, left: r.left, width: r.width, height: r.height }
}

// Tour genérico e reutilizável: dado um storageKey e uma lista de passos
// (seletor CSS + texto), mostra um destaque (spotlight) sobre cada elemento
// na ordem, com botões Anterior/Próximo/Pular. Só aparece uma vez por
// navegador -- guardamos isso em localStorage, não no backend, porque é uma
// preferência de UI pura, não um dado que precise sincronizar entre dispositivos.
export default function GuidedTour({ storageKey, steps, onStepChange }: GuidedTourProps) {
  const [active, setActive] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (localStorage.getItem(storageKey)) return
    // dá um instante pro DOM (tabs, preview, etc) terminar de montar antes de medir
    const timer = setTimeout(() => setActive(true), 400)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey])

  useEffect(() => {
    if (!active) return
    const step = steps[stepIndex]
    if (!step) return

    onStepChange?.(stepIndex)
    setRect(null)

    // dá um instante pro parent reagir (ex: trocar de aba) e o DOM atualizar
    // antes de medir a posição do elemento alvo deste passo
    const measureTimer = setTimeout(() => setRect(getRect(step.selector)), 50)
    const update = () => setRect(getRect(step.selector))
    window.addEventListener('resize', update)
    const interval = setInterval(update, 300)
    return () => {
      clearTimeout(measureTimer)
      window.removeEventListener('resize', update)
      clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, stepIndex, steps])

  const finish = () => {
    localStorage.setItem(storageKey, '1')
    setActive(false)
  }

  const next = () => {
    if (stepIndex >= steps.length - 1) {
      finish()
      return
    }
    setStepIndex((i) => i + 1)
  }

  const prev = () => setStepIndex((i) => Math.max(0, i - 1))

  if (!active) return null

  const step = steps[stepIndex]
  const padding = 8

  return (
    <div className="fixed inset-0 z-[100]">
      <div className="absolute inset-0 bg-black/60" onClick={finish} />

      {rect && (
        <div
          className="absolute rounded-lg ring-4 ring-indigo-500 pointer-events-none transition-all duration-200"
          style={{
            top: rect.top - padding,
            left: rect.left - padding,
            width: rect.width + padding * 2,
            height: rect.height + padding * 2,
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.6)',
          }}
        />
      )}

      <div
        className="absolute bg-white rounded-lg shadow-xl p-4 w-72 max-w-[calc(100vw-2rem)]"
        style={
          rect
            ? {
                top: Math.min(rect.top + rect.height + padding + 8, window.innerHeight - 180),
                left: Math.min(Math.max(rect.left, 16), window.innerWidth - 304),
              }
            : { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
        }
      >
        <p className="text-xs font-medium text-indigo-600 mb-1">
          Passo {stepIndex + 1} de {steps.length}
        </p>
        <h3 className="font-semibold text-gray-900 mb-1">{step.title}</h3>
        <p className="text-sm text-gray-600 mb-4">{step.text}</p>
        <div className="flex items-center justify-between">
          <button type="button" onClick={finish} className="text-xs text-gray-400 hover:text-gray-600">
            Pular
          </button>
          <div className="flex gap-2">
            {stepIndex > 0 && (
              <button
                type="button"
                onClick={prev}
                className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Anterior
              </button>
            )}
            <button
              type="button"
              onClick={next}
              className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              {stepIndex >= steps.length - 1 ? 'Concluir' : 'Próximo'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
