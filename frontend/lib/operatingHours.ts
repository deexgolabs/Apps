// Porta em JS do app/utils.py::is_within_operating_hours do backend — mesma
// sintaxe (dia:abre-fecha por linha, dia aceita intervalo "seg-sex" ou único).
const WEEKDAY_ALIASES: Record<string, number> = {
  dom: 0, seg: 1, ter: 2, qua: 3, qui: 4, sex: 5, sab: 6, sáb: 6,
}
// JS Date.getDay(): domingo=0 ... sábado=6 (mesma numeração usada aqui)

function parseDayRange(token: string): number[] | null {
  token = token.trim().toLowerCase()
  if (token.includes('-')) {
    const [startS, endS] = token.split('-')
    const start = WEEKDAY_ALIASES[startS.trim()]
    const end = WEEKDAY_ALIASES[endS.trim()]
    if (start === undefined || end === undefined) return null
    if (start <= end) {
      return Array.from({ length: end - start + 1 }, (_, i) => start + i)
    }
    return [...Array.from({ length: 7 - start }, (_, i) => start + i), ...Array.from({ length: end + 1 }, (_, i) => i)]
  }
  const day = WEEKDAY_ALIASES[token]
  return day !== undefined ? [day] : null
}

export function isWithinOperatingHours(horarioText: string, now: Date = new Date()): boolean {
  if (!(horarioText || '').trim()) return true

  const weekday = now.getDay()
  const currentMinutes = now.getHours() * 60 + now.getMinutes()

  for (const rawLine of horarioText.split('\n')) {
    const line = rawLine.trim()
    if (!line || !line.includes(':')) continue
    const firstColon = line.indexOf(':')
    const dayPart = line.slice(0, firstColon)
    const hoursPart = line.slice(firstColon + 1).trim()
    const days = parseDayRange(dayPart)
    if (!days || !days.includes(weekday)) continue
    if (!hoursPart.includes('-')) continue
    const [openS, closeS] = hoursPart.split('-')
    const [openH, openM] = openS.trim().split(':').map(Number)
    const [closeH, closeM] = closeS.trim().split(':').map(Number)
    if ([openH, openM, closeH, closeM].some((n) => isNaN(n))) continue
    const openMinutes = openH * 60 + openM
    const closeMinutes = closeH * 60 + closeM
    if (currentMinutes >= openMinutes && currentMinutes <= closeMinutes) return true
  }

  return false
}
