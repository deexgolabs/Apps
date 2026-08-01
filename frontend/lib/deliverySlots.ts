export interface PickupPoint {
  name: string
  address: string
}

/** "Nome: Endereço" por linha -- mesmo formato chave:valor usado em várias
 * outras configs desta plataforma (frete, horário de funcionamento). */
export function parsePickupPoints(text: string): PickupPoint[] {
  return (text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, ...rest] = line.split(':')
      return { name: (name || '').trim(), address: rest.join(':').trim() }
    })
    .filter((p) => p.name)
}

export interface DeliverySlot {
  label: string
  value: string
}

const DAY_LABELS = ['Hoje', 'Amanhã']

/** Gera opções de horário (hoje/amanhã) a partir de janelas "HH:MM-HH:MM"
 * configuradas pelo dono, uma por linha -- pula horários de hoje que já
 * passaram, pra nunca oferecer um slot que não dá mais tempo de cumprir. */
export function generateDeliverySlots(janelaText: string, now: Date = new Date()): DeliverySlot[] {
  const windows = (janelaText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [start, end] = line.split('-').map((s) => s.trim())
      return { start, end }
    })
    .filter((w) => /^\d{1,2}:\d{2}$/.test(w.start) && /^\d{1,2}:\d{2}$/.test(w.end))

  const slots: DeliverySlot[] = []
  const nowMinutes = now.getHours() * 60 + now.getMinutes()

  DAY_LABELS.forEach((dayLabel, dayOffset) => {
    for (const w of windows) {
      const [startH, startM] = w.start.split(':').map(Number)
      const startMinutes = startH * 60 + startM
      if (dayOffset === 0 && startMinutes <= nowMinutes) continue
      slots.push({ label: `${dayLabel} ${w.start}-${w.end}`, value: `${dayLabel} ${w.start}-${w.end}` })
    }
  })

  return slots
}
