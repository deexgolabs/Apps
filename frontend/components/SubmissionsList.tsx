'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import toast from 'react-hot-toast'

interface Submission {
  id: number
  data: Record<string, any>
  created_at: string
}

export default function SubmissionsList({ appId, moduleName }: { appId: string; moduleName: string }) {
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSubmissions = async () => {
      try {
        const response = await api.get(`/api/apps/${appId}/modules/${moduleName}/submissions`)
        setSubmissions(response.data)
      } catch (error) {
        toast.error('Erro ao carregar respostas')
      } finally {
        setLoading(false)
      }
    }
    fetchSubmissions()
  }, [appId, moduleName])

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>

  if (submissions.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        Nenhuma resposta recebida ainda. Teste o formulário na aba Preview.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">Respostas recebidas ({submissions.length})</p>
      {submissions.map((submission) => (
        <div key={submission.id} className="border border-gray-200 rounded-lg p-3 text-sm">
          <p className="text-xs text-gray-400 mb-1">
            {new Date(submission.created_at).toLocaleString('pt-BR')}
          </p>
          {Object.entries(submission.data).map(([key, value]) => (
            <p key={key} className="text-gray-700">
              <span className="font-medium">{key}:</span> {String(value)}
            </p>
          ))}
        </div>
      ))}
    </div>
  )
}
