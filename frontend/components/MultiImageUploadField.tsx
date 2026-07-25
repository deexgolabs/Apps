'use client'

import { useRef, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface MultiImageUploadFieldProps {
  label: string
  value: string[]
  onChange: (urls: string[]) => void
  max?: number
  hint?: string
}

export default function MultiImageUploadField({ label, value, onChange, max = 6, hint }: MultiImageUploadFieldProps) {
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/api/uploads/image', formData, {
        headers: { 'Content-Type': undefined },
      })
      onChange([...value, response.data.url])
    } catch (error: any) {
      const detail = error.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Erro ao enviar imagem')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const removeAt = (index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} ({value.length}/{max})
      </label>
      {hint && <p className="text-xs text-gray-400 -mt-1.5 mb-2">{hint}</p>}
      <div className="flex flex-wrap gap-2 mb-2">
        {value.map((url, index) => (
          <div key={index} className="relative">
            <img src={url} alt="" className="w-16 h-16 object-cover rounded-lg border border-gray-300" />
            <button
              type="button"
              onClick={() => removeAt(index)}
              className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-600 text-white text-xs leading-none"
              aria-label="Remover imagem"
            >
              ×
            </button>
          </div>
        ))}
      </div>
      {value.length < max && (
        <div>
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            onChange={handleFileChange}
            disabled={uploading}
            className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-600 file:font-semibold hover:file:bg-indigo-100 disabled:opacity-50"
          />
          {uploading && <p className="text-xs text-gray-400 mt-1">Enviando...</p>}
        </div>
      )}
    </div>
  )
}
