'use client'

import { useRef, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface ImageUploadFieldProps {
  label: string
  value: string
  onChange: (url: string) => void
  hint?: string
}

export default function ImageUploadField({ label, value, onChange, hint }: ImageUploadFieldProps) {
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      // A instância `api` tem Content-Type: application/json fixo por padrão — precisa
      // virar `undefined` aqui pra deixar o navegador montar o header multipart com o
      // boundary certo sozinho (um valor fixo sem boundary quebra o parsing no backend).
      const response = await api.post('/api/uploads/image', formData, {
        headers: { 'Content-Type': undefined },
      })
      onChange(response.data.url)
    } catch (error: any) {
      const detail = error.response?.data?.detail
      // Erros de validação (422) do FastAPI vêm como lista de objetos, não string —
      // passar isso direto pro toast quebra a renderização (objeto como filho React).
      toast.error(typeof detail === 'string' ? detail : 'Erro ao enviar imagem')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      {hint && <p className="text-xs text-gray-400 -mt-1.5 mb-2">{hint}</p>}
      {value ? (
        <div className="flex items-center gap-3">
          <img src={value} alt="" className="w-16 h-16 object-cover rounded-lg border border-gray-300" />
          <button
            type="button"
            onClick={() => onChange('')}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Remover
          </button>
        </div>
      ) : (
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
