'use client'

import { isWithinOperatingHours } from '@/lib/operatingHours'

export default function OperatingHoursBadge({ horarioFuncionamento }: { horarioFuncionamento?: string }) {
  if (!horarioFuncionamento?.trim()) return null

  const open = isWithinOperatingHours(horarioFuncionamento)

  return (
    <span
      className={`inline-block text-[11px] font-semibold px-2 py-0.5 rounded-full mb-2 ${
        open ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      }`}
    >
      {open ? 'Aberto agora' : 'Fechado'}
    </span>
  )
}
