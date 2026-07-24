'use client'

interface PlatformToggleProps {
  value: 'android' | 'ios'
  onChange: (value: 'android' | 'ios') => void
}

// Alterna só a decoração visual do PhoneFrame (notch/home indicator no iOS,
// barra de navegação no Android) — preferência momentânea, não é salva.
export default function PlatformToggle({ value, onChange }: PlatformToggleProps) {
  return (
    <div className="flex gap-1 mb-2 w-fit mx-auto">
      {(['android', 'ios'] as const).map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onChange(p)}
          className={`px-3 py-1 text-xs rounded-lg font-medium ${
            value === p ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}
        >
          {p === 'android' ? 'Android' : 'iOS'}
        </button>
      ))}
    </div>
  )
}
