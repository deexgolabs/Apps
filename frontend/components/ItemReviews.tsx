'use client'

import { useEffect, useState } from 'react'
import { publicApi } from '@/lib/api'
import { endUserAuthHeader, endUserSessionKey } from '@/lib/endUserAuth'
import type { ItemReview } from '@/types'
import toast from 'react-hot-toast'

export default function ItemReviews({ appId, moduleName, itemId }: { appId: string; moduleName: string; itemId: number }) {
  const [reviews, setReviews] = useState<ItemReview[]>([])
  const [loading, setLoading] = useState(true)
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [sending, setSending] = useState(false)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    setLoggedIn(!!localStorage.getItem(endUserSessionKey(appId)))
  }, [appId])

  const fetchReviews = async () => {
    try {
      const res = await publicApi.get<ItemReview[]>(
        `/api/apps/${appId}/public/modules/${moduleName}/items/${itemId}/reviews`
      )
      setReviews(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReviews()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId, moduleName, itemId])

  const handleSubmit = async () => {
    setSending(true)
    try {
      await publicApi.post(
        `/api/apps/${appId}/modules/${moduleName}/items/${itemId}/reviews`,
        { rating, comment: comment || null },
        { headers: endUserAuthHeader(appId) }
      )
      setComment('')
      toast.success('Avaliação enviada!')
      fetchReviews()
    } catch {
      toast.error('Erro ao enviar avaliação')
    } finally {
      setSending(false)
    }
  }

  if (loading) return <p className="text-xs text-gray-400">Carregando avaliações...</p>

  const avg = reviews.length ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length : null

  return (
    <div className="space-y-2 mt-2 border-t border-gray-100 pt-2">
      <p className="text-xs font-semibold text-gray-600">
        Avaliações {avg != null && `· ${'★'.repeat(Math.round(avg))} (${reviews.length})`}
      </p>

      {loggedIn && (
        <div className="space-y-1.5">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                className={n <= rating ? 'text-yellow-500' : 'text-gray-300'}
              >
                ★
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Comentário (opcional)"
            className="w-full text-xs border border-gray-200 rounded px-2 py-1"
            rows={2}
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={sending}
            className="text-xs bg-indigo-600 text-white px-2 py-1 rounded disabled:opacity-50"
          >
            Enviar avaliação
          </button>
        </div>
      )}

      <div className="space-y-1.5">
        {reviews.map((r) => (
          <div key={r.id} className="text-xs">
            <span className="text-yellow-500">{'★'.repeat(r.rating)}</span>{' '}
            <span className="font-medium">{r.end_user_name}</span>
            {r.comment && <p className="text-gray-500">{r.comment}</p>}
          </div>
        ))}
      </div>
    </div>
  )
}
