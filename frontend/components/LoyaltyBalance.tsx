'use client'

import { useEffect, useState } from 'react'
import { publicApi } from '@/lib/api'
import { endUserAuthHeader, endUserSessionKey } from '@/lib/endUserAuth'

export default function LoyaltyBalance({
  appId,
  settings,
}: {
  appId: string
  settings: Record<string, any> | undefined
}) {
  const [points, setPoints] = useState<number | null>(null)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    const hasSession = !!localStorage.getItem(endUserSessionKey(appId))
    setLoggedIn(hasSession)
    if (!hasSession) return
    publicApi
      .get(`/api/apps/${appId}/loyalty/me`, { headers: endUserAuthHeader(appId) })
      .then((res) => setPoints(res.data.points))
      .catch(() => {})
  }, [appId])

  return (
    <div className="text-center space-y-3">
      <h3 className="font-semibold text-gray-900">{settings?.titulo || 'Cartão Fidelidade'}</h3>
      {settings?.regra && <p className="text-sm text-gray-600">{settings.regra}</p>}
      {loggedIn ? (
        <p className="text-2xl font-bold text-indigo-600">
          {points === null ? '...' : points} <span className="text-sm font-normal text-gray-500">pontos</span>
        </p>
      ) : (
        <p className="text-xs text-gray-400 italic">Faça login para ver seu saldo de pontos</p>
      )}
      {settings?.premio && (
        <p className="text-sm text-gray-700">
          Prêmio: <span className="font-semibold">{settings.premio}</span>
        </p>
      )}
    </div>
  )
}
