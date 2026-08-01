'use client'

import { SUPPORTED_LANGUAGES, useLanguage, type Language } from '@/lib/i18n'

export default function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage()

  return (
    <select
      value={language}
      onChange={(e) => setLanguage(e.target.value as Language)}
      aria-label="Idioma"
      className="bg-transparent text-white text-xs border border-white/40 rounded px-1 py-0.5"
    >
      {SUPPORTED_LANGUAGES.map((lang) => (
        <option key={lang.code} value={lang.code} className="text-gray-900">
          {lang.label}
        </option>
      ))}
    </select>
  )
}
